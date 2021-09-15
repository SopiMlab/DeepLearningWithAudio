import os

from . import common

def add_parser(subparsers):
    ddsp_parser = subparsers.add_parser("ddsp")
    
    ddsp_subparsers = ddsp_parser.add_subparsers(dest="subcommand", required=True)
    
    ddsp_setup_parser = ddsp_subparsers.add_parser("setup")
    ddsp_setup_parser.add_argument("--repo")

def setup(args):
    runner = common.Runner()    
    runner.basic_setup()
    runner.ensure_repo("ddsp")
    runner.ensure_conda_env("ddsp")
    runner.ensure_pip_install("ddsp", [], [common.repo_dir("ddsp")])
    
subcommands = {
    "setup": setup
}

