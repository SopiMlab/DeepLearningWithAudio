import argparse

from . import common

def add_parser(subparsers):
    util_parser = subparsers.add_parser("util")

    util_subparsers = util_parser.add_subparsers(dest="subcommand", required=True)

    util_run_parser = util_subparsers.add_parser("run")
    util_run_parser.add_argument("args", nargs=argparse.REMAINDER)

    util_screen_attach_parser = util_subparsers.add_parser("screen-attach")

    util_screen_kill_parser = util_subparsers.add_parser("screen-kill")

def run(args):
    runner = common.Runner()
    cmd = args.args
    runner.run_with_conda(cmd)

def screen_attach(args):
    runner = common.Runner()
    name = runner.screen_name
    runner.run_script(f"attach {name} screen", [["screen", "-Dr", name]], capture_output=False)

def screen_kill(args):
    runner = common.Runner()
    name = runner.screen_name
    runner.run_script(f"kill {name} screen", [["screen", "-S", name, "-X", "kill"]], capture_output=False)

subcommands = {
    "run": run,
    "screen-attach": screen_attach,
    "screen-kill": screen_kill
}
