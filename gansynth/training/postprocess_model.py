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
    log("no stage contains a {} file".format(ckpt_fn))
    sys.exit(1)

log("latest stage with checkpoint: {}".format(latest_stage_dir))

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

def set_meta_path_op(train_meta_path, json_path):
    def _run():
        with open(json_path, "r") as fp:
            data = json.load(fp)

        data["train_meta_path"] = "./{}".format(train_meta_path)

        with open(json_path, "w") as fp:
            json.dump(data, fp)

    return (
        "set train_meta_path = {} in {}".format(train_meta_path, json_path),
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

new_meta_path = os.path.join(ckpt_dir, "meta.json")
if os.path.exists(new_meta_path):
    ops.append(delete_op(new_meta_path))

ops.append(copy_op(meta_path, new_meta_path))

ops.append(set_meta_path_op(os.path.basename(new_meta_path), experiment_path))

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
