import argparse

from lib import common
import lib.ddsp
import lib.gansynth

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=True)

lib.ddsp.add_parser(subparsers)
lib.gansynth.add_parser(subparsers)

import os
import shlex
import subprocess
import sys
import traceback

command_modules = {
    "ddsp": lib.ddsp,
    "gansynth": lib.gansynth
}

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
