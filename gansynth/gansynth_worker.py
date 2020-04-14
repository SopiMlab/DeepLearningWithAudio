from __future__ import print_function

import os
import random
import struct
import sys

import numpy as np

from magenta.models.gansynth.lib import flags as lib_flags
from magenta.models.gansynth.lib import generate_util as gu
from magenta.models.gansynth.lib import model as lib_model
from magenta.models.gansynth.lib import util
import tensorflow as tf

import sopilib.communication_struct as gss
from sopilib.handlers import handlers
from sopilib.utils import print_err, read_msg

try:
    ckpt_dir = sys.argv[1]
    batch_size = int(sys.argv[2])
except IndexError:
    print_err("usage: {} checkpoint_dir batch_size".format(os.path.basename(__file__)))
    sys.exit(1)

flags = lib_flags.Flags({"batch_size_schedule": [batch_size]})
model = lib_model.Model.load_from_path(ckpt_dir, flags)

stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)
stdout.write(gss.to_tag_msg(gss.OUT_TAG_INIT))

audio_length = model.config['audio_length']
sample_rate = model.config['sample_rate']
info_msg = gss.to_info_msg(audio_length=audio_length, sample_rate=sample_rate)
stdout.write(info_msg)
stdout.flush()

while True:
    in_tag_msg = read_msg(stdin, gss.tag_struct.size)
    in_tag = gss.from_tag_msg(in_tag_msg)
    
    if in_tag not in handlers:
        raise ValueError("unknown input message tag: {}".format(in_tag))

    handlers[in_tag](model, stdin, stdout)
