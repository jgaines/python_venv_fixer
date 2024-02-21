"""Find and migrate Python virtual environments to a new manager.

This script allows you to find and migrate Python virtual environments from
one virtual environment manager to another.  It is intended to be used
when transitioning to a new virtual environment manager.  For example, when
switching from using pyenv to using mise, you have to rebuild all of your
virtual environments to use mise. Then you can remove the old pyenv
installation.
"""

import argparse

__version__ = "0.1.0"


def process_args(args):
    """Process the command-line arguments."""
    argparser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0], epilog=__doc__.split("\n", maxsplit=1)[1]
    )
    argparser.add_argument(
        "directories",
        nargs="*",
        help="The directories to search recursively for Python Virtual Environments (default: %(default)s).",
        default=["."],
    )
    argparser.add_argument("--ignore", "-i", help="Ignore the specified directories.", action="append")
    argparser.add_argument("--dry-run", "-n", help="Do not make any changes.", action="store_true")
    argparser.add_argument("--target", "-t", help="The target virtual environment manager (default: %(default)s).", choices=["mise", "pyenv", "rtx"], default="mise")
    argparser.add_argument("--version", "-V", action="version", version=__version__)
    return argparser.parse_args(args)


def main(args=None):
    """The main entry point for the command-line interface."""
    args = process_args(args)
    print(args)
