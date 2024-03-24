# vefixer (WIP)

Find and migrate Python virtual environments to a new manager.

This script allows you to find and migrate Python virtual environments from
one virtual environment manager to another.  It is intended to be used
when transitioning to a new virtual environment manager.  For example, when
switching from using pyenv to using mise, you have to rebuild all of your
virtual environments to use mise. Then you can remove the old pyenv
installation.

I doubt I'll do any more work on this unless I get totally repulsed by nix and
nixOS.  My goal is to get away from using the various language managers (mise)
and pipx and various other custom scripts I use for my system setup, updating
and development and switch to using nix and nixOS for everything.
