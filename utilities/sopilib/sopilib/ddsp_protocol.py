from __future__ import print_function

import struct

import numpy as np

IN_TAG_TIMBRE_TRANSFER = 0

OUT_TAG_INIT = 0
OUT_TAG_TIMBRE_TRANSFERRED = 1

# tag: message type identifier
tag_struct = struct.Struct("I")

# timbre_transfer: input sample rate, output sample rate, f0 octave shift, f0 confidence threshold, loudness db shift, ckpt path length, source audio length, (ckpt path, source audio)
timbre_transfer_struct = struct.Struct("IIdddLL")

# timbre_transferred: audio length
timbre_transferred_struct = struct.Struct("L")

def simple_conv(msg_struct):
    to_msg = lambda *args: msg_struct.pack(*args)
    from_msg = lambda msg: (lambda t: t if len(t) > 1 else t[0])(msg_struct.unpack(msg))

    return to_msg, from_msg

to_tag_msg, from_tag_msg = simple_conv(tag_struct)

to_timbre_transfer_msg, from_timbre_transfer_msg = simple_conv(timbre_transfer_struct)    

to_timbre_transferred_msg, from_timbre_transferred_msg = simple_conv(timbre_transferred_struct)

to_str_msg = lambda s: s.encode("utf-8")
from_str_msg = lambda s: s.decode("utf-8")

def to_audio_msg(buf):
    return buf.tobytes()

def from_audio_msg(msg):
    return np.frombuffer(msg, dtype=np.float32)
