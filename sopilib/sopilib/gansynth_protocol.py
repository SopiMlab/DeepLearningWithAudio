from __future__ import print_function

import struct
import sys

import numpy as np
import math


Z_SIZE = 256

# init: audio length, sample rate
init_struct = struct.Struct("i" * 2)

# tag: integer denoting the type of message
tag_struct = struct.Struct("i")

# z: latent vector as 256 doubles
z_struct = struct.Struct(Z_SIZE*"d")

# f64: double-precision float
f64_struct = struct.Struct("d")

# slerp_z: source 0, source 1, interpolation amount
slerp_z_struct = struct.Struct(z_struct.format + z_struct.format + f64_struct.format)

# count: integer denoting a number of items
count_struct = struct.Struct("i")

# gen_audio: pitch, z
gen_audio_struct = struct.Struct("i" + (Z_SIZE*"d"))

# audio_size: length of audio data
audio_size_struct = struct.Struct("i")

# hallucinate: note count, interpolation steps, spacing, start trim, attack, sustain, release
hallucinate_struct = struct.Struct("i" * 2 + "d" * 5)

IN_TAG_RAND_Z = 0
IN_TAG_SLERP_Z = 1
IN_TAG_GEN_AUDIO = 2
IN_TAG_HALLUCINATE = 3

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

def to_info_msg(audio_length, sample_rate):
    return init_struct.pack(audio_length, sample_rate)

def from_info_msg(msg):
    return init_struct.unpack(msg)

def to_z_msg(z):
    return z_struct.pack(*z)

def from_z_msg(msg):
    return np.array(z_struct.unpack(msg), dtype=np.float64)

to_audio_size_msg, from_audio_size_msg = simple_conv(audio_size_struct)

to_f64_msg, from_f64_msg = simple_conv(f64_struct)

def to_slerp_z_msg(z0, z1, amount):
    return to_z_msg(z0) + to_z_msg(z1) + to_f64_msg(amount)

def from_slerp_z_msg(msg):
    z_size = z_struct.size
    f64_size = f64_struct.size
    assert len(msg) == 2 * z_size + f64_size
    z0 = from_z_msg(msg[ : z_size])
    z1 = from_z_msg(msg[z_size : 2*z_size])
    amount = from_f64_msg(msg[2*z_size : ])
    return z0, z1, amount

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
    note_count, interpolation_steps, spacing, start_trim, attack, sustain, release = hallucinate_struct.unpack(msg)
    spacing = math.floor(spacing * 100)/100.0
    start_trim = math.floor(start_trim * 100)/100.0
    attack = math.floor(attack * 100)/100.0
    sustain = math.floor(sustain * 100)/100.0
    release = math.floor(release * 100)/100.0
    return (note_count, interpolation_steps, spacing, start_trim, attack, sustain, release)
