import argparse
import os

from . import common

def add_parser(subparsers):
    samplernn_parser = subparsers.add_parser("samplernn")
    
    samplernn_subparsers = samplernn_parser.add_subparsers(dest="subcommand", required=True)
    
    samplernn_setup_parser = samplernn_subparsers.add_parser("setup")

    samplernn_chunk_parser = samplernn_subparsers.add_parser("chunk-audio")
    samplernn_chunk_parser.add_argument("--input_name", required=True)
    samplernn_chunk_parser.add_argument("--output_name")
    samplernn_chunk_parser.add_argument("--custom", action="store_true")
    samplernn_chunk_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    samplernn_train_parser = samplernn_subparsers.add_parser("train")
    samplernn_train_parser.add_argument("--input_name", required=True)
    samplernn_train_parser.add_argument("--model_name", required=True)
    samplernn_train_parser.add_argument("--preset", default="lstm-linear-skip")
    samplernn_train_parser.add_argument("--custom", action="store_true")
    samplernn_train_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

def setup(args):
    runner = common.Runner()
    runner.ensure_repo("prism-samplernn")
    runner.ensure_conda_env("samplernn")
    runner.ensure_pip_install("samplernn", [], [common.repo_dir("prism-samplernn")])

def chunk_audio(args):
    runner = common.Runner()
    runner.require_conda_env("samplernn")
    out_name = args.output_name or f"{args.input_name}_chunked"
    in_dir = common.input_dir(args.input_name)
    out_dir = common.input_dir(out_name)
    custom = args.custom
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    wav_files = [os.path.join(in_dir, fn) for fn in os.listdir(in_dir) if fn.lower().endswith(".wav")]
    if not wav_files:
        raise common.DlwaAbort(f"no .wav files found in input directory: {in_dir}")
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise common.DlwaAbort(f"output path already exists and is non-empty: {out_dir}")
    extra_args = common.process_remainder(args.extra_args)
    defaults = [
        "--chunk_length", "8000",
        "--overlap", "1000"
    ] if not custom else []
    chunk_cmds = []
    for wav_file in wav_files:
        chunk_cmds.append([
            "python", "-m", "samplernn_scripts.chunk_audio",
            "--input_file", wav_file,
            "--output_dir", out_dir,
            *defaults,
            *extra_args
        ])
    chunk_script = [
        *runner.conda_activate_script(runner.env_name("samplernn")),
        *chunk_cmds
    ]
    runner.run_script(f"chunk audio for samplernn", chunk_script, capture_output=False)

def train(args):
    runner = common.Runner()
    runner.require_conda_env("samplernn")
    runner.require_no_screen()
    input_dir = common.input_dir(args.input_name)
    model_name = args.model_name
    model_dir = common.model_dir("samplernn", model_name)
    preset = args.preset
    custom = args.custom
    extra_args = common.process_remainder(args.extra_args)
    if not os.path.exists(input_dir):
        raise common.DlwaAbort(f"input directory does not exist: {input_dir}")
    if os.path.exists(model_dir) and os.listdir(model_dir):
        raise common.DlwaAbort(f"model output path already exists and is non-empty: {model_dir}")
    if not custom:
        defaults = [
            "--batch_size", "128",
            "--checkpoint_every", "5",
            "--sample_rate", "16000",
            "--config_file", os.path.join(common.misc_dir, "samplernn", f"{preset}.config.json")
        ]
    else:
        defaults = []
    log_path = os.path.join(model_dir, "dlwa_train.log")
    train_script = [
        *runner.conda_activate_script(runner.env_name("samplernn")),
        [
            "python", "-m", "samplernn_scripts.train",
            "--id", model_name,
            "--logdir_root", common.model_dir("samplernn"),
            "--data_dir", input_dir,
            *defaults,
            *extra_args
        ]
    ]
    train_screen_script = runner.make_screen_script(train_script, log_path)
    os.mkdir(model_dir)
    runner.run_script(f"train gansynth model in screen", train_screen_script, capture_output=False)
    
subcommands = {
    "setup": setup,
    "chunk-audio": chunk_audio,
    "train": train
}
