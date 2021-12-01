import argparse
import json
import os

from . import common

def add_parser(subparsers):
    gansynth_parser = subparsers.add_parser("gansynth")
    
    gansynth_subparsers = gansynth_parser.add_subparsers(dest="subcommand", required=True)
    
    gansynth_setup_parser = gansynth_subparsers.add_parser("setup")
    
    gansynth_chop_parser = gansynth_subparsers.add_parser("chop-audio")
    gansynth_chop_parser.add_argument("--input_name", required=True)
    gansynth_chop_parser.add_argument("--output_name")
    gansynth_chop_parser.add_argument("extra_args", nargs=argparse.REMAINDER)
    
    gansynth_pad_parser = gansynth_subparsers.add_parser("pad-audio")
    gansynth_pad_parser.add_argument("--input_name", required=True)
    gansynth_pad_parser.add_argument("--output_name")
    gansynth_pad_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    gansynth_make_dataset_parser = gansynth_subparsers.add_parser("make-dataset")
    gansynth_make_dataset_parser.add_argument("--input_name", required=True)
    gansynth_make_dataset_parser.add_argument("--dataset_name", required=True)
    gansynth_make_dataset_parser.add_argument("extra_args", nargs=argparse.REMAINDER)
    
    gansynth_train_parser = gansynth_subparsers.add_parser("train")
    gansynth_train_parser.add_argument("--dataset_name", required=True)
    gansynth_train_parser.add_argument("--model_name", required=True)
    gansynth_train_parser.add_argument("--custom", action="store_true")
    gansynth_train_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    gansynth_ganspace_parser = gansynth_subparsers.add_parser("ganspace")
    gansynth_ganspace_parser.add_argument("--model_name", required=True)
    gansynth_ganspace_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

def setup(args):
    runner = common.Runner()
    runner.ensure_repo("magenta")
    runner.ensure_conda_env("gansynth")
    runner.ensure_pip_install("gansynth", [], [common.repo_dir("magenta")])
    apply_protobuf_workaround = True
    if apply_protobuf_workaround:
        runner.ensure_repo("protobuf")
        protobuf_workaround_script = [
            *runner.conda_activate_script(runner.env_name("gansynth")),
            ["cd", common.repo_dir("protobuf")],
            "git submodule update --init --recursive",
            "./autogen.sh",
            "cd python",
            "python setup.py build",
            f"{runner.conda_envvars()} conda remove --yes --force protobuf libprotobuf",
            "python setup.py develop"
        ]
        runner.run_script(f"apply protobuf workaround", protobuf_workaround_script, capture_output=False)

def chop_audio(args):
    runner = common.Runner()
    runner.require_conda_env("gansynth")
    out_name = args.output_name or f"{args.input_name}_chopped"
    in_dir = common.input_dir(args.input_name)
    out_dir = common.input_dir(out_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    if not any(True for fn in os.listdir(in_dir) if fn.lower().endswith(".wav")):
        raise common.DlwaAbort(f"no .wav files found in input directory: {in_dir}")
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise common.DlwaAbort(f"output path already exists and is non-empty: {out_dir}")
    extra_args = common.process_remainder(args.extra_args)
    chop_script = [
        *runner.conda_activate_script(runner.env_name("gansynth")),
        ["gansynth_chop_audio", in_dir, out_dir, *extra_args]
    ]
    runner.run_script(f"chop audio for gansynth", chop_script, capture_output=False)
    
def pad_audio(args):
    runner = common.Runner()
    runner.require_conda_env("gansynth")
    out_name = args.output_name or f"{args.input_name}_padded"
    in_dir = common.input_dir(args.input_name)
    out_dir = common.input_dir(out_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    if not any(True for fn in os.listdir(in_dir) if fn.lower().endswith(".wav")):
        raise common.DlwaAbort(f"no .wav files found in input directory: {in_dir}")
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise common.DlwaAbort(f"output path already exists and is non-empty: {out_dir}")
    extra_args = common.process_remainder(args.extra_args)
    chop_script = [
        *runner.conda_activate_script(runner.env_name("gansynth")),
        ["gansynth_pad_audio", in_dir, out_dir, *extra_args]
    ]
    runner.run_script(f"pad audio for gansynth", chop_script, capture_output=False)
    
def make_dataset(args):
    runner = common.Runner()
    runner.require_conda_env("gansynth")
    in_dir = common.input_dir(args.input_name)
    out_dir = common.dataset_dir("gansynth", args.dataset_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    if not any(True for fn in os.listdir(in_dir) if fn.lower().endswith(".wav")):
        raise common.DlwaAbort(f"no .wav files found in input directory: {in_dir}")
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise common.DlwaAbort(f"dataset output path already exists and is non-empty: {out_dir}")
    extra_args = common.process_remainder(args.extra_args)
    make_dataset_script = [
        *runner.conda_activate_script(runner.env_name("gansynth")),
        ["gansynth_make_dataset", "--in_dir", in_dir, "--out_dir", out_dir, *extra_args]
    ]
    runner.run_script(f"make gansynth dataset", make_dataset_script, capture_output=False)

def train(args):
    runner = common.Runner()
    runner.require_conda_env("gansynth")
    runner.require_no_screen()
    dataset_dir = common.dataset_dir("gansynth", args.dataset_name)
    model_dir = common.model_dir("gansynth", args.model_name)
    custom = args.custom
    extra_args = common.process_remainder(args.extra_args)
    if not os.path.exists(dataset_dir):
        raise common.DlwaAbort(f"dataset directory does not exist: {dataset_dir}")
    if os.path.exists(model_dir) and os.listdir(model_dir):
        raise common.DlwaAbort(f"model output path already exists and is non-empty: {model_dir}")
    dataset_pat = os.path.join(dataset_dir, "data.tfrecord*")
    dataset_pat_q = common.gin_quote_str(dataset_pat)
    if not custom:
        hparams = {
            "train_data_path": os.path.join(dataset_dir, "data.tfrecord"),
            "train_meta_path": os.path.join(dataset_dir, "meta.json"),
            "train_root_dir": os.path.join(model_dir),
            "dataset_name": "nsynth_tfrecord",
            "save_graph_def": False,
            "save_summaries_num_images": 0
        }
        hparams_json = json.dumps(hparams)
        defaults = [
            "--config=mel_prog_hires",
            f"--hparams={hparams_json}"
        ]
    else:
        defaults = []
    log_path = os.path.join(model_dir, "dlwa_train.log")
    train_script = [
        *runner.conda_activate_script(runner.env_name("gansynth")),
        [
            "gansynth_train",
            *defaults,
            *extra_args
        ]
    ]
    train_screen_script = runner.make_screen_script(train_script, log_path)
    os.mkdir(model_dir)
    runner.run_script(f"train gansynth model in screen", train_screen_script, capture_output=False)

def ganspace(args):
    runner = common.Runner()
    runner.require_conda_env("gansynth")
    runner.require_no_screen()
    model_dir = common.model_dir("gansynth", args.model_name)
    extra_args = common.process_remainder(args.extra_args)
    if not os.path.exists(model_dir):
        raise common.DlwaAbort(f"model directory does not exist: {model_dir}")
    log_path = os.path.join(model_dir, "dlwa_ganspace.log")
    ganspace_script = [
        *runner.conda_activate_script(runner.env_name("gansynth")),
        [
            "gansynth_ganspace",
            "--ckpt_dir", model_dir,
            # TODO: set reasonable defaults in script, implement --pca_out_dir with auto filename
            "--random_z_count", "8192",
            "--pca_out_file", os.path.join(model_dir, "ganspace.pickle"),
            *extra_args
        ]
    ]
    ganspace_screen_script = runner.make_screen_script(ganspace_script, log_path)
    # os.mkdir(model_dir) # TODO: make dir once we have pca_out_dir?
    runner.run_script(f"run ganspace on gansynth model", ganspace_screen_script, capture_output=False)
    
subcommands = {
    "setup": setup,
    "chop-audio": chop_audio,
    "pad-audio": pad_audio,
    "make-dataset": make_dataset,
    "train": train,
    "ganspace": ganspace
}
