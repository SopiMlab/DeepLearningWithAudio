import argparse
import os

from . import common

def add_parser(subparsers):
    ddsp_parser = subparsers.add_parser("ddsp")
    
    ddsp_subparsers = ddsp_parser.add_subparsers(dest="subcommand", required=True)
    
    ddsp_setup_parser = ddsp_subparsers.add_parser("setup")
    ddsp_setup_parser.add_argument("--repo")

    ddsp_make_dataset_parser = ddsp_subparsers.add_parser("make-dataset")
    ddsp_make_dataset_parser.add_argument("--input_name", required=True)
    ddsp_make_dataset_parser.add_argument("--dataset_name", required=True)
    ddsp_make_dataset_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    ddsp_train_parser = ddsp_subparsers.add_parser("train")
    ddsp_train_parser.add_argument("--dataset_name", required=True)
    ddsp_train_parser.add_argument("--model_name", required=True)
    ddsp_train_parser.add_argument("--custom", action="store_true")
    ddsp_train_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

def setup(args):
    runner = common.Runner()
    runner.ensure_repo("ddsp")
    runner.ensure_conda_env("ddsp")
    runner.ensure_pip_install("ddsp", [], [common.repo_dir("ddsp")])

def make_dataset(args):
    runner = common.Runner()
    runner.require_conda_env("ddsp")
    in_dir = common.input_dir(args.input_name)
    out_dir = common.dataset_dir("ddsp", args.dataset_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    if not any(True for fn in os.listdir(in_dir) if fn.lower().endswith(".wav")):
        raise common.DlwaAbort(f"no .wav files found in input directory: {in_dir}")
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise common.DlwaAbort(f"dataset output path already exists and is non-empty: {out_dir}")
    in_patterns = os.path.join(in_dir, "*.wav")
    out_path = os.path.join(out_dir, "data.tfrecord")
    extra_args = common.process_remainder(args.extra_args)
    make_dataset_script = [
        *runner.conda_activate_script(runner.env_name("ddsp")),
        ["ddsp_prepare_tfrecord", "--input_audio_filepatterns", in_patterns, "--output_tfrecord_path", out_path, *extra_args]
    ]
    runner.run_script(f"make ddsp dataset", make_dataset_script, capture_output=False)

def train(args):
    runner = common.Runner()
    runner.require_conda_env("ddsp")
    runner.require_no_screen()
    dataset_dir = common.dataset_dir("ddsp", args.dataset_name)
    model_dir = common.model_dir("ddsp", args.model_name)
    custom = args.custom
    extra_args = common.process_remainder(args.extra_args)
    if not os.path.exists(dataset_dir):
        raise common.DlwaAbort(f"dataset directory does not exist: {dataset_dir}")
    if os.path.exists(model_dir) and os.listdir(model_dir):
        raise common.DlwaAbort(f"model output path already exists and is non-empty: {model_dir}")
    dataset_pat = os.path.join(dataset_dir, "data.tfrecord*")
    dataset_pat_q = common.gin_quote_str(dataset_pat)
    defaults = [
        "--gin_file", "models/solo_instrument.gin",
        "--gin_file", "datasets/tfrecord.gin",
        "--gin_param", "batch_size=16",
        "--gin_param", "train_util.train.num_steps=30000",
        "--gin_param", "train_util.train.steps_per_save=300",
        "--gin_param", "train_util.Trainer.checkpoints_to_keep=10"
    ] if not custom else []
    train_script = [
        *runner.conda_activate_script(runner.env_name("ddsp")),
        [
            "ddsp_run",
            "--alsologtostderr",
            "--mode", "train",            
            *defaults,
            "--gin_param", f"TFRecordProvider.file_pattern={dataset_pat_q}",
            "--save_dir", model_dir,
            *extra_args
        ]
    ]
    log_path = os.path.join(model_dir, "dlwa_train.log")
    train_screen_script = runner.make_screen_script(train_script, log_path)
    os.mkdir(model_dir)
    runner.run_script(f"train ddsp model in screen", train_screen_script, capture_output=False)

subcommands = {
    "setup": setup,
    "make-dataset": make_dataset,
    "train": train
}
