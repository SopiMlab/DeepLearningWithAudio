from __future__ import print_function

import argparse
import json
import os
import pkgutil
import re
import sys
from types import SimpleNamespace

import numpy as np
from samplernn_scripts import generate as gen

import sopilib.samplernn_protocol as protocol
from sopilib.utils import print_err, read_msg

from handlers import handlers

parser = argparse.ArgumentParser()
parser.add_argument("--config", default=None)
parser.add_argument("--canvas_dir", default=".")
parser.add_argument("--num_seqs", type=int, default=1)
parser.add_argument("--ckpt_dir")

args = parser.parse_args()

config_file = args.config
if config_file != None:
    config_file = os.path.join(args.canvas_dir, config_file)
    with open(config_file, "rb") as fp:
        config = json.load(fp)
else:
    config = json.loads(pkgutil.get_data("samplernn_scripts", "conf/default.config.json"))

print_err("config:", config)
    
max_ckpt = None
for fn in os.listdir(args.ckpt_dir):
    m = re.match(r"^(model\.ckpt-(\d+))\.index$", fn)
    if m:
        num = int(m.group(2))
        if max_ckpt == None or max_ckpt[1] < num:
            max_ckpt = (m.group(1), num)

if max_ckpt == None:
    print_err("no model.ckpt-#.index files found in checkpoint dir")
    sys.exit(1)

ckpt_path = os.path.join(args.ckpt_dir, max_ckpt[0])

print_err("ckpt_path:", ckpt_path)

model = gen.create_inference_model(ckpt_path, args.num_seqs, config)

print_err("hello :)")

# open standard input/output handles

stdin = sys.stdin.buffer
stdout = sys.stdout.buffer

# write init message

stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_INIT))
stdout.flush()

print_err("it begins @_@")

state = SimpleNamespace(
    stdin = stdin,
    stdout = stdout,
    config = config,
    num_seqs = args.num_seqs,
    model = model
)

while True:
    in_tag_msg = read_msg(stdin, protocol.tag_struct.size)
    in_tag = protocol.from_tag_msg(in_tag_msg)
    
    if in_tag not in handlers:
        raise ValueError("unknown input message tag: {}".format(in_tag))

    handlers[in_tag](state)
