from __future__ import absolute_import
from __future__ import print_function

import argparse
import json
import os
import re
import shutil
import sys

parser = argparse.ArgumentParser()

parser.add_argument("--ckpt_dir", required=True)
parser.add_argument("--meta_path", required=True)
parser.add_argument("--execute", action="store_true")

args = parser.parse_args()

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

ckpt_dir = args.ckpt_dir
meta_path = args.meta_path

# check that the argument paths exist

if not os.path.isdir(ckpt_dir):
    log("no such directory: {}".format(ckpt_dir))
    sys.exit(1)

if not os.path.isfile(meta_path):
    log("no such file: {}".format(meta_path))
    sys.exit(1)

# check that there is an experiment.json
    
experiment_fn = "experiment.json"
experiment_path = os.path.join(ckpt_dir, experiment_fn)

if not os.path.isfile(experiment_path):
    log("file {} not found in {}".format(experiment_fn, ckpt_dir))
    sys.exit(1)

# find all the stage_##### subdirectories

stage_dirs = []

for fn in os.listdir(ckpt_dir):
    path = os.path.join(ckpt_dir, fn)
    
    if not os.path.isdir(path):
        continue

    m = re.match(r"^stage_\d+$", fn)

    if not m:
        continue

    stage_dirs.append(path)

if not stage_dirs:
    log("no stage directories found in {}".format(ckpt_dir))
    sys.exit(1)

log("found {} stage directories".format(len(stage_dirs)))
        
# find the latest stage that contains a checkpoint file

stage_dirs.sort(reverse=True)

latest_stage_dir = None

ckpt_fn = "checkpoint"

for stage_dir in stage_dirs:
    ckpt_path = os.path.join(stage_dir, ckpt_fn)
    if os.path.isfile(ckpt_path):
        latest_stage_dir = stage_dir
        break

if not latest_stage_dir:
    log("no stage found with a {} file".format(ckpt_fn))
    sys.exit(1)

log("latest stage with checkpoint: {}".format(latest_stage_dir))

# find the latest training iteration

# build a dict mapping iteration numbers to their data, index and meta files
training_iterations = {}
for fn in os.listdir(latest_stage_dir):
    m = re.match(r"^model\.ckpt-(\d+)\.(.+)$", fn)
    if not m:
        continue

    iteration = m.group(1)
    ext = m.group(2)

    if iteration not in training_iterations:
        training_iterations[iteration] = {
            "data": None,
            "index": None,
            "meta": None
        }

    filemap = training_iterations[iteration]
        
    if ext.startswith("data-"):
        filemap["data"] = fn
    elif ext == "index":
        filemap["index"] = fn
    elif ext == "meta":
        filemap["meta"] = fn

# find the latest iteration that has all three required files
latest_iteration = None
for iteration in sorted(training_iterations.keys(), reverse=True):
    filemap = training_iterations[iteration]
    if filemap["data"] != None and filemap["index"] != None and filemap["meta"] != None:
        latest_iteration = iteration
        break

if not latest_iteration:
    log("no iteration found with data, index and meta files")
    sys.exit(1)

log("latest iteration with data, index and meta files: {}".format(latest_iteration))
    
# collect postprocessing operations

def delete_op(path):
    def _run():
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    return (
        "delete {}".format(path),
        _run
    )

def copy_op(src_path, dst_path):
    def _run():
        shutil.copy(src_path, dst_path)

    return (
        "copy {} to {}".format(src_path, dst_path),
        _run
    )

def cleanup_experiment_json_op(json_path):
    def _run():
        with open(json_path, "r") as fp:
            data = json.load(fp)

        if "train_root_dir" in data:
            del data["train_root_dir"]

        if "train_meta_path" in data:
            del data["train_meta_path"]

        with open(json_path, "w") as fp:
            json.dump(data, fp)

    return (
        "clean up {}".format(json_path),
        _run
    )

def fix_ckpt_paths_op(ckpt_path):
    def _run():
        from google.protobuf import text_format
        from tensorflow.python.training.checkpoint_state_pb2 import CheckpointState

        with open(ckpt_path, "rb") as fp:
            ckpt_str = fp.read()
        
        ckpt = CheckpointState()
        text_format.Merge(ckpt_str, ckpt)

        new_ckpt = CheckpointState()
        new_ckpt.model_checkpoint_path = "./{}".format(os.path.basename(ckpt.model_checkpoint_path))
        
        with open(ckpt_path, "wb") as fp:
            fp.write(text_format.MessageToBytes(new_ckpt))

    return (
        "set relative model_checkpoint_path in {}".format(ckpt_path),
        _run
    )

ops = []

passed_latest_stage_dir = False
for stage_dir in stage_dirs:
    if passed_latest_stage_dir:
        for fn in os.listdir(stage_dir):
            path = os.path.join(stage_dir, fn)
            ops.append(delete_op(path))
    elif stage_dir == latest_stage_dir:
        passed_latest_stage_dir = True
    else:
        ops.append(delete_op(stage_dir))

latest_stage_files_to_keep = list(training_iterations[latest_iteration].values())
latest_stage_files_to_keep.append("checkpoint")
for fn in os.listdir(latest_stage_dir):
    if fn not in latest_stage_files_to_keep:
        ops.append(delete_op(os.path.join(latest_stage_dir, fn)))
        
new_meta_path = os.path.join(ckpt_dir, "meta.json")
if os.path.exists(new_meta_path):
    ops.append(delete_op(new_meta_path))

ops.append(copy_op(meta_path, new_meta_path))

ops.append(cleanup_experiment_json_op(experiment_path))

ops.append(fix_ckpt_paths_op(os.path.join(latest_stage_dir, ckpt_fn)))

# list or perform postprocessing operations

execute = args.execute

log()
if execute:
    log("performing postprocessing operations...")
else:
    log("the following postprocessing operations are required:")

for desc, run in ops:
    log("  - {}".format(desc))
    if execute:
        run()

if not execute:
    log()
    log("make sure your data is backed up and run this command with the --execute flag to perform the operations")
