"""Find and migrate Python virtual environments to a new manager.

This script allows you to find and migrate Python virtual environments from
one virtual environment manager to another.  It is intended to be used
when transitioning to a new virtual environment manager.  For example, when
switching from using pyenv to using mise, you have to rebuild all of your
virtual environments to use mise. Then you can remove the old pyenv
installation.
"""

import argparse
import os
import re
from pathlib import Path
import subprocess
from typing import Sequence

__version__ = "0.1.0"
default_ignore = [
    ".git",
    ".idea",
    ".local",
    ".pdm-build",
    ".pex",
    ".pyenv",
    ".pytest_cache",
    ".ruff_cache",
    ".rye",
    ".tox",
    "__pycache__",
    "dist",
    "pipx",
]


def process_args(args):
    """Process the command-line arguments."""
    argparser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0], epilog=__doc__.split("\n", maxsplit=1)[1]
    )
    argparser.add_argument(
        "directories",
        nargs="*",
        type=Path,
        help="The directories to search recursively for Python Virtual Environments (default: %(default)s).",
        default=[Path(".")],
    )
    argparser.add_argument(
        "--ignore",
        "-i",
        help="Ignore the specified directories (default: %(default)s).",
        action="append",
        default=default_ignore,
    )
    argparser.add_argument(
        "--debug",
        "-d",
        help="Enable debug mode, prints out stderr of commands run.",
        action="store_true",
    )
    argparser.add_argument(
        "--dry-run", "-n", help="Do not make any changes.", action="store_true"
    )
    argparser.add_argument(
        "--target",
        "-t",
        help="The target virtual environment manager (default: %(default)s).",
        choices=["mise", "pyenv", "rtx"],
        default="mise",
    )
    argparser.add_argument(
        "--verbose", "-v", help="Increase verbosity.", action="count", default=0
    )
    argparser.add_argument("--version", "-V", action="version", version=__version__)
    return argparser.parse_args(args)


def find_virtual_environments(
    directories: Sequence[Path], ignore: Sequence[str] = [], verbose: int = 0
):
    """Find all virtual environments in the directory recursively.

    Return as generator.
    """
    while directories:
        top = directories.pop()
        for p in top.iterdir():
            if verbose > 2:
                print(f"Checking {p}")
            if p.is_dir():
                if p.name in ignore:
                    continue
                if not p.is_symlink():  # don't follow symlinked directories
                    directories.append(p)
            elif p.name == "python" and p.is_symlink() and p.parent.name == "bin":
                yield p.parent.parent, p.resolve()


python_version_pattern = re.compile(r"^\d+\.\d+(\.\d+)?$")


def is_a_version(part: str):
    """Check if a part of a path is a version number."""
    # compare part to a regex matching a version number
    if python_version_pattern.match(part):
        return True


def extract_python_version(symlink: Path):
    """Extract the Python version from the python symlink."""
    for i, part in enumerate(symlink.parts):
        if part == "python" and is_a_version(symlink.parts[i + 1]):
            return symlink.parts[i + 1]


def find_requirements_file(directory: Path):
    """Find the requirements file in the directory."""

    def search_in(directory: Path):
        # Quick sanity check to make sure directory exists and is a directory.
        if not directory.is_dir():
            return None

        # First look at files in the directory.
        # This check is pretty generic and will work for many projects in the wild.
        found_docker_directory = False
        for p in directory.iterdir():
            if p.name == "requirements.txt":
                return p
            elif p.name == "docker":
                found_docker_directory = True
        # The following checks are more specific to my use case.
        # Then look to see if there is a requirements file in a docker directory.
        if found_docker_directory and (p := search_in(directory / "docker")):
            return p

    if p := search_in(directory):
        return p
    # The following checks are more specific to my use case.
    # if we're in the administrator branch, look for the corresponding eng-tools project.
    if directory.parent.name == "administrator":
        if p := search_in(directory.parent.with_name("eng-tools") / directory.name):
            return p
    # if we're in the eng-tools branch, look for the corresponding administrator project.
    if directory.parent.name == "eng-tools":
        if p := search_in(directory.parent.with_name("administrator") / directory.name):
            return p
    return None


def change_dir(path: Path, dry_run: bool, verbose: int = 0):
    """Change to the specified directory."""
    if dry_run:
        print(f"Would change to {path}")
    else:
        if verbose > 1:
            print(f"Changing to {path}")
        os.chdir(path)


def run_command(cmd, dry_run, verbose, debug):
    """Optionally run a command and optionally print the output based on flags and result.

    Returns the stdout of the command if it was successful, otherwise None."""
    if not dry_run:
        if debug or verbose > 2:
            print(f"Running: {cmd}")
        result = subprocess.run(cmd, capture_output=True)
        if debug or result.returncode != 0 or verbose > 2:
            print(f"stdout: {result.stdout.decode()}")
            print(f"stderr: {result.stderr.decode()}")
            print(f"return code: {result.returncode}")
        if result.returncode != 0:
            return None
    else:
        print(f"Would run: {cmd}")
        return "/tmp"
    return result.stdout.decode().strip() or "OK"


def fix_virtual_environment(
    virtual_environment: Path,
    symlink: Path,
    target: str,
    dry_run: bool,
    verbose: int = 0,
    debug: bool = False,
):
    """Fix the virtual environment to use the new manager."""
    print("--------------------")
    python_version = extract_python_version(symlink)
    # execute target manager to get the path to the python executable
    # mise exec python@3.10.7 -- python -c 'import sys; print(sys.executable)'
    if target == "mise":
        target_path = run_command(
            [
                "mise",
                "exec",
                f"python@{python_version}",
                "--",
                "python",
                "-c",
                "import sys; print(sys.executable)",
            ],
            dry_run,
            verbose,
            debug,
        )
        if dry_run:
            # Fake target_path for dry_run so we can get reasonable results
            if "mise/installs/python" in str(symlink):
                target_path = str(symlink)
            else:
                target_path = f"/blah/mise/installs/python/{python_version}/bin/python"
    elif target == "pyenv":
        target_path = None
    elif target == "rtx":
        target_path = None

    if verbose > 0:
        print(f"Found {symlink} in {virtual_environment} for version {python_version}.")
        print(f"Target path: {target_path}")

    if not target_path:
        print(
            f"Could not find a path to the {target} python executable for version {python_version}."
        )
        return

    if not target_path:
        print(
            f"Could not find a path to the {target} python executable for version {python_version}."
        )
        return
    if verbose > 0:
        print(f"Fixing {virtual_environment} to use {target_path}...")
    parent_files = list(p.name for p in virtual_environment.parent.iterdir())

    reinstall_packages = False
    if Path(target_path).exists() and symlink.samefile(target_path):
        print(f"Skipping {virtual_environment}, it is already using {target}.")
    elif target == "mise":
        print(f"Attempting to use mise to rebuild {virtual_environment}.")
        if not run_command(
            ["rm", "-rf", str(virtual_environment)], dry_run, verbose, debug
        ):
            return
        if not run_command(
            [
                "mise",
                "exec",
                f"python@{python_version}",
                "--",
                "python",
                "-m",
                "venv",
                str(virtual_environment),
            ],
            dry_run,
            verbose,
            debug,
        ):
            return
        reinstall_packages = True
    elif target == "rtx":
        print("No support for RTX yet because my use case is moving to mise.")
        return
    elif target == "pyenv":
        print("No support for pyenv yet because my use case is moving to mise.")
        return

    if reinstall_packages:
        if "pdm.lock" in parent_files:
            print(
                f"Found pdm.lock in {virtual_environment.parent} using pdm to restore packages."
            )
            change_dir(virtual_environment.parent, dry_run, verbose)
            if not run_command(["pdm", "install"], dry_run, verbose, debug):
                return
        elif requirements_file := find_requirements_file(virtual_environment.parent):
            print(f"Found {requirements_file} using pip to restore packages.")
            change_dir(virtual_environment.parent, dry_run, verbose)
            if not run_command(
                ["pip", "install", "-r", str(requirements_file)],
                dry_run,
                verbose,
                debug,
            ):
                return
        else:
            print(f"I don't know how to restore packages in {virtual_environment}.")

    if ".rtx.toml" in parent_files and target == "mise":
        print(
            f"Found .rtx.toml in {virtual_environment.parent}, renaming to .mise.toml"
        )
        change_dir(virtual_environment.parent, dry_run, verbose)
        if not run_command(["mv", ".rtx.toml", ".mise.toml"], dry_run, verbose, debug):
            return


def main(args=None):
    """The main entry point for the command-line interface."""
    args = process_args(args)
    for virtual_environment, symlink in find_virtual_environments(
        list(d.resolve() for d in args.directories), args.ignore, args.verbose
    ):
        fix_virtual_environment(
            virtual_environment,
            symlink,
            args.target,
            args.dry_run,
            args.verbose,
            args.debug,
        )


if __name__ == "__main__":
    main()
