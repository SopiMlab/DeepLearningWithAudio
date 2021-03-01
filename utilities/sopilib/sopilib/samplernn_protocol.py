from __future__ import print_function

import struct

import numpy as np

IN_TAG_GENERATE = 0

OUT_TAG_INIT = 0
OUT_TAG_GENERATED = 1

# tag: message type identifier
tag_struct = struct.Struct("I")

# generate: seed sample rate, output sample rate, number of outputs, output audio length, seed audio length, (temperatures, seed audio)
generate_struct = struct.Struct("IIILL")

# generated: output sample rate, number of outputs, output audio length, (output audios)
generated_struct = struct.Struct("IIL")

def simple_conv(msg_struct):
    to_msg = lambda *args: msg_struct.pack(*args)
    from_msg = lambda msg: (lambda t: t if len(t) > 1 else t[0])(msg_struct.unpack(msg))

    return to_msg, from_msg

to_tag_msg, from_tag_msg = simple_conv(tag_struct)

to_generate_msg, from_generate_msg = simple_conv(generate_struct)

to_generated_msg, from_generated_msg = simple_conv(generated_struct)

to_str_msg = lambda s: s.encode("utf-8")
from_str_msg = lambda s: s.decode("utf-8")

f32_struct = struct.Struct("f")

to_f32_msg, from_f32_msg = simple_conv(f32_struct)

def to_audio_msg(buf):
    return buf.tobytes()

def from_audio_msg(msg):
    return np.frombuffer(msg, dtype=np.float32)
