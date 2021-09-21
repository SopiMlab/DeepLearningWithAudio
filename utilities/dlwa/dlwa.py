#!/usr/bin/env python3
import argparse

from lib import common
import lib.ddsp
import lib.gansynth
import lib.util

parser = argparse.ArgumentParser()

import os
import shlex
import subprocess
import sys
import traceback

command_modules = {
    "ddsp": lib.ddsp,
    "gansynth": lib.gansynth,
    "util": lib.util
}

subparsers = parser.add_subparsers(dest="command", required=True)
for key, mod in command_modules.items():
    mod.add_parser(subparsers)

args = parser.parse_args()

try:
    command_modules[args.command].subcommands[args.subcommand](args)
except common.DlwaAbort as e:
    print()
    print(e)
    print("aborting!")
    sys.exit(1)
else:
    print()
    print("done!")
