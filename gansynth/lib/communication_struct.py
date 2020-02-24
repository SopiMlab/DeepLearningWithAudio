from __future__ import print_function

import struct
import sys

import numpy as np

Z_SIZE = 256

tag_struct = struct.Struct("i")
z_struct = struct.Struct(Z_SIZE*"d")
count_struct = struct.Struct("i")
gen_audio_struct = struct.Struct("i" + (Z_SIZE*"d"))
audio_size_struct = struct.Struct("i")
hallucinate_struct = struct.Struct("i" * 2 + "d" * 5)

IN_TAG_RAND_Z = 0
IN_TAG_GEN_AUDIO = 1
IN_TAG_HALLUCINATE = 2

OUT_TAG_INIT = 0
OUT_TAG_Z = 1
OUT_TAG_AUDIO = 2

def simple_conv(msg_struct):
    to_msg = lambda *args: msg_struct.pack(*args)
    from_msg = lambda msg: msg_struct.unpack(msg)[0]

    return to_msg, from_msg

to_tag_msg, from_tag_msg = simple_conv(tag_struct)

to_count_msg, from_count_msg = simple_conv(count_struct)

def to_gen_msg(pitch, z):
    return gen_audio_struct.pack(pitch, *z)

def from_gen_msg(msg):
    data = gen_audio_struct.unpack(msg)
    pitch = data[0]
    z = np.array(data[1:], dtype=np.float64)
    return pitch, z

def to_z_msg(z):
    return z_struct.pack(*z)

def from_z_msg(msg):
    return np.array(z_struct.unpack(msg), dtype=np.float64)

to_audio_size_msg, from_audio_size_msg = simple_conv(audio_size_struct)

def to_audio_msg(buf):
    return buf.tobytes()

def from_audio_msg(msg):
    return np.frombuffer(msg, dtype=np.float32)


def to_hallucinate_msg(note_count, 
                        interpolation_steps, 
        spacing = 0.2,
        start_trim = 0.0,
        attack = 0.5,
        sustain = 0.5,
        release = 0.5):
    return hallucinate_struct.pack(note_count, interpolation_steps, spacing, start_trim, attack, sustain, release)

def from_hallucinate_msg(msg):
    return hallucinate_struct.unpack(msg)