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

import gansynth_struct as gss

try:
    ckpt_dir = sys.argv[1]
    batch_size = int(sys.argv[2])
except IndexError:
    print("usage: {} checkpoint_dir batch_size".format(os.path.basename(__file__)))
    sys.exit(1)

flags = lib_flags.Flags({"batch_size_schedule": [batch_size]})
model = lib_model.Model.load_from_path(ckpt_dir, flags)

stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
stdout = os.fdopen(sys.stdout.fileno(), "wb", 0)

def read_msg(size):
    msg = stdin.read(size)

    if not msg:
        raise EOFError("stdin")

    return msg

def handle_rand_z():
    count_msg = read_msg(gss.count_struct.size)
    count = gss.from_count_msg(count_msg)

    zs = model.generate_z(count)
    
    stdout.write(gss.to_tag_msg(gss.OUT_TAG_Z))
    stdout.write(gss.to_count_msg(len(zs)))

    for z in zs:
        stdout.write(gss.to_z_msg(z))

def handle_gen_audio():
    count_msg = read_msg(gss.count_struct.size)
    count = gss.from_count_msg(count_msg)

    pitches = []
    zs = []
    for i in xrange(count):
        gen_msg = read_msg(gss.gen_audio_struct.size)
        pitch, z = gss.from_gen_msg(gen_msg)
        
        pitches.append(pitch)
        zs.append(z)

    z_arr = np.array(zs)
    audios = model.generate_samples_from_z(z_arr, pitches)
    
    stdout.write(gss.to_tag_msg(gss.OUT_TAG_AUDIO))
    stdout.write(gss.to_count_msg(len(audios)))

    for audio in audios:
        stdout.write(gss.to_audio_size_msg(audio.size * audio.itemsize))
        stdout.write(gss.to_audio_msg(audio))

handlers = {
    gss.IN_TAG_RAND_Z: handle_rand_z,
    gss.IN_TAG_GEN_AUDIO: handle_gen_audio
}

stdout.write(gss.to_tag_msg(gss.OUT_TAG_INIT))

while True:
    in_tag_msg = read_msg(gss.tag_struct.size)
    in_tag = gss.from_tag_msg(in_tag_msg)
    
    if in_tag not in handlers:
        raise ValueError("unknown input message tag: {}".format(in_tag))

    handlers[in_tag]()
