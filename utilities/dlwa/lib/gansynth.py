def add_parser(subparsers):
    gansynth_parser = subparsers.add_parser("gansynth")
    gansynth_subparsers = gansynth_parser.add_subparsers(dest="subcommand", required=True)
    
    gansynth_setup_parser = gansynth_subparsers.add_parser("setup")
