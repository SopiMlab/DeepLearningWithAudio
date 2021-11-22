import argparse
import bisect
import json
import os
import re
import shlex

from . import common

def add_parser(subparsers):
    nsynth_parser = subparsers.add_parser("nsynth")
    
    nsynth_subparsers = nsynth_parser.add_subparsers(dest="subcommand", required=True)
    
    nsynth_setup_parser = nsynth_subparsers.add_parser("setup")    
    download_model_parser = nsynth_subparsers.add_parser("download-model")

    prepare_parser = nsynth_subparsers.add_parser("prepare")
    prepare_parser.add_argument("--input_name", required=True)
    prepare_parser.add_argument("--output_name", default=None)

    generate_parser = nsynth_subparsers.add_parser("generate")
    generate_parser.add_argument("--input_name", required=True)
    generate_parser.add_argument("--output_name", default=None)
    generate_parser.add_argument("--batch_size", type=int, default=256)
    generate_parser.add_argument("--batch", type=int, default=0)
    generate_parser.add_argument("--gpu", type=int, default=0)

def setup(args):
    runner = common.Runner()
    runner.ensure_repo("magenta-v1")
    runner.ensure_repo("open-nsynth-super")
    runner.ensure_conda_env("magenta-v1-build")
    build_script = [
        *runner.conda_activate_script(runner.env_name("magenta-v1-build")),
        ["cd", common.repo_dir("magenta-v1")],
        ["python", "setup.py", "bdist_wheel", "--universal", "--gpu"],
    ]
    runner.run_script(f"build magenta-gpu", build_script, capture_output=False)
    runner.ensure_conda_env("nsynth")
    install_script = [
        *runner.conda_activate_script(runner.env_name("nsynth")),
        ["cd", common.repo_dir("magenta-v1")],
        f"wheel=$(find dist -iname 'magenta_gpu-*.whl')",
        f'num_wheels=$(echo "$wheel" | wc -l)',
        f'if [ "$num_wheels" -ne 1 ]; then',
        f'  echo "found $num_wheels files matching dist/magenta_gpu-*.whl (expected 1)"',
        f'  exit 1',
        f"fi",
        f'pip install "$wheel"',
    ]
    runner.run_script("install magenta-gpu", install_script, capture_output=False)
    remove_build_env_script = [
        *runner.conda_prep_script(),
        ["conda", "env", "remove", "-n", runner.env_name("magenta-v1-build")]
    ]
    runner.run_script("remove build environment", remove_build_env_script, capture_output=False)
    
def download_model(args):
    runner = common.Runner()
    runner.require_conda_env("nsynth")
    model_url = "http://download.magenta.tensorflow.org/models/nsynth/wavenet-ckpt.tar"
    model_name = "wavenet-ckpt"
    model_dir = os.path.join(common.model_dir("nsynth", model_name))
    model_dir_exists = os.path.exists(model_dir)
    if model_dir_exists and "checkpoint" in os.listdir(model_dir):
        raise common.DlwaAbort(f"model output path already exists and contains checkpoint file: {model_dir}")
    model_tar_path = os.path.join(model_dir, f"{model_name}.tar")
    if not model_dir_exists:
        os.makedirs(model_dir)
    model_dir_inner = os.path.join(model_dir, model_name)
    download_script = [
        ["wget", "-c", "-O", model_tar_path, model_url],
        ["tar", "xvf", model_tar_path, "-C", model_dir],
        ["find", model_dir_inner, "-mindepth", "1", "-maxdepth", "1", "-not", "-name", ".*", "-exec", "mv", "{}", model_dir, ";"],
        ["rm", "-rf", model_dir_inner],
        ["rm", model_tar_path]
    ]
    runner.run_script(f"download model", download_script, capture_output=False)

def prepare(args):
    runner = common.Runner()
    runner.ensure_conda_env("nsynth")
    in_dir = common.input_dir(args.input_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    out_name = args.output_name or args.input_name
    out_dir = common.output_dir("nsynth", out_name)
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    settings_fn = "settings.json"
    settings_path = os.path.join(out_dir, settings_fn)
    if os.path.exists(settings_path):
        raise common.DlwaAbort(f"settings file already exists: {settings_path}")
    sounds = {}
    for fn in os.listdir(in_dir):
        name, ext = os.path.splitext(fn)
        if ext.lower() != ".wav" or name.startswith("."):
            continue
        m = re.match(r"^(.+)_(\d+)", name)
        if not m:
            continue
        sound = m.group(1)
        pitch = int(m.group(2))
        if sound not in sounds:
            sounds[sound] = set()
        sounds[sound].add(pitch)
    if not sounds:
        raise common.DlwaAbort("no files found matching '[sound]_[pitch].wav'")
    sound_names = sorted(sounds.keys())
    if len(sounds) < 4:
        raise common.DlwaAbort(f"less than 4 sounds found: {sound_names}")
    shared_pitches = None
    outlier_pitches = set()
    for sound, pitches in sounds.items():
        if shared_pitches is None:
            shared_pitches = pitches
        else:
            new_outlier_pitches = shared_pitches.difference(pitches).union(pitches.difference(shared_pitches))
            outlier_pitches = outlier_pitches.union(new_outlier_pitches)
            shared_pitches = shared_pitches.union(pitches).difference(new_outlier_pitches)
    print(f"found sounds: {sound_names}")
    print(f"with pitches: {sorted(shared_pitches)}")
    if outlier_pitches:
        raise common.DlwaAbort(f"mismatching pitches - pitches found for some sounds but not all: {sorted(outlier_pitches)}")
    create_workdir_script = [
        ["cd", out_dir],
        ["mkdir", "-p", "workdir"],
        ["cd", "workdir"],
        ["mkdir", "-p", "embeddings_input", "embeddings_output", "embeddings_batched", "audio_output", "pads_output"],
        f"if [ ! -e audio_input ]; then",
        f"  ln -s {shlex.quote(in_dir)} audio_input",
        f"fi"
    ]
    runner.run_script(f"create workdir structure if needed", create_workdir_script, capture_output=False)
    print()
    sound_names_dist = ([],[],[],[])
    for i, sound in enumerate(sound_names):
        sound_names_dist[i%len(sound_names_dist)].append(sound)
    settings = {
        "pads": {
            "NW": sound_names_dist[0],
            "NE": sound_names_dist[1],
            "SW": sound_names_dist[2],
            "SE": sound_names_dist[3]
        },
        "magenta_dir": common.repo_dir("magenta-v1"),
        "pitches": sorted(shared_pitches),
        "resolution": 9,
        "final_length": 60000,
        "gpus": 1
    }
    print("generated settings:")
    settings_str = json.dumps(settings, indent=2)
    print(settings_str)
    print(f"saving settings to {settings_path}")
    with open(settings_path, "w") as fp:
        fp.write(settings_str)

def generate(args):
    runner = common.Runner()
    runner.ensure_conda_env("nsynth")
    in_dir = common.input_dir(args.input_name)
    if not os.path.exists(in_dir):
        raise common.DlwaAbort(f"input directory does not exist: {in_dir}")
    out_name = args.output_name or args.input_name
    out_dir = common.output_dir("nsynth", out_name)
    nsynth_workdir = os.path.join(common.repo_dir("open-nsynth-super"), "audio", "workdir")
    model_dir = os.path.join(common.model_dir("nsynth", "wavenet-ckpt"))
    workdir = os.path.join(out_dir, "workdir")
    script_prelude = [
        *runner.conda_activate_script(runner.env_name("nsynth")),
        ["cd", workdir],
    ]
    audio_input_path = os.path.join(workdir, "audio_input")
    embeddings_input_path = os.path.join(workdir, "embeddings_input")
    checkpoint_path = os.path.join(model_dir, "model.ckpt-200000")
    save_embeddings_script = [
        *script_prelude,
        f"""if [ "$(find {shlex.quote(embeddings_input_path)} -iname '*.npy' | wc -l)" -gt 0 ]; then""",
        f"  echo 'existing embeddings found, skipping'",
        f"  exit 0",
        f"fi",
        [
            "nsynth_save_embeddings",
            f"--checkpoint_path={checkpoint_path}",
            f"--source_path={audio_input_path}",
            f"--save_path={embeddings_input_path}",
            f"--batch_size=64"
        ],
    ]
    runner.run_script(f"save embeddings", save_embeddings_script, capture_output=False)    
    embeddings_output_path = os.path.join(workdir, "embeddings_output")
    embeddings_batched_path = os.path.join(workdir, "embeddings_batched")
    embeddings_batched_batch_path = os.path.join(embeddings_batched_path, f"batch{args.batch}")
    compute_new_embeddings_script = [
        *script_prelude,
        f"""if [ "$(find {shlex.quote(embeddings_batched_batch_path)} {shlex.quote(embeddings_output_path)} -iname '*.npy' | wc -l)" -gt 0 ]; then""",
        f"  echo 'existing embeddings found, skipping'",
        f"  exit 0",
        f"fi",
        ["python", os.path.join(nsynth_workdir, "02_compute_new_embeddings.py")],        
    ]
    runner.run_script(f"compute new embeddings", compute_new_embeddings_script, capture_output=False)    
    batch_embeddings_script = [
        *script_prelude,
        f"""if [ "$(find {shlex.quote(embeddings_batched_batch_path)} -iname '*.npy' | wc -l)" -gt 0 ]; then""",
        f"  echo 'existing embeddings found, skipping'",
        f"  exit 0",
        f"fi",
        ["python", os.path.join(nsynth_workdir, "03_batch_embeddings.py")],
    ]
    runner.run_script(f"batch embeddings", batch_embeddings_script, capture_output=False)    
    audio_output_path = os.path.join(workdir, "audio_output")
    audio_output_batch_path = os.path.join(audio_output_path, f"batch{args.batch}")
    batch_size = args.batch_size
    gpu_number = args.gpu
    samples_per_save = 300000    
    log_path = os.path.join(out_dir, "dlwa_nsynth_generate.log")
    # FIXME: Aalto-specific
    prep_cuda_script = [["module", "load", "cuda/10.0.130"]] if runner.check_lmod() else []
    generate_script = [
        *script_prelude,
        *prep_cuda_script,
        [
            "nsynth_generate",
            f"--alsologtostderr",
            f"--checkpoint_path={checkpoint_path}",
            f"--source_path={embeddings_batched_batch_path}",
            f"--save_path={audio_output_batch_path}",
            f"--batch_size={batch_size}",
            f"--gpu_number={gpu_number}",
            f"--samples_per_save={samples_per_save}"
        ]
    ]
    generate_screen_script = runner.make_screen_script(generate_script, log_path)
    runner.run_script(f"generate in screen", generate_screen_script, capture_output=False)

subcommands = {
    "setup": setup,
    "download-model": download_model,
    "prepare": prepare,
    "generate": generate
}
