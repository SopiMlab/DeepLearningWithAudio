import argparse
import contextlib
import os
import sys
import time

import numpy as np
from samplernn import (dequantize, quantize)
from samplernn_scripts import generate as gen
import tensorflow as tf

import sopilib.samplernn_protocol as protocol
from sopilib.utils import print_err, read_msg

stderr_linebuf = open(sys.stderr.fileno(), "w", 1)

def generate(state, sample_rate, dur, temperature, seed):
    with contextlib.redirect_stdout(stderr_linebuf):
        yield from gen.generate(state.model, state.num_seqs, dur, sample_rate, temperature, seed)
    
def handle_generate(state):
    stdin = state.stdin
    stdout = state.stdout
    model = state.model
    config = state.config
    num_seqs = state.num_seqs
    
    generate_msg = read_msg(stdin, protocol.generate_struct.size)
    seed_sr, out_sr, num_outs, dur, seed_len = protocol.from_generate_msg(generate_msg)

    print_err("seed_sr =", seed_sr)
    print_err("out_sr =", out_sr)
    print_err("num_outs =", num_outs)
    print_err("dur =", dur)
    print_err("seed_len =", seed_len)

    if seed_len > 0:
        seed_msg = read_msg(stdin, seed_len * protocol.f32_struct.size)
        seed_audio = protocol.from_audio_msg(seed_msg)
    else:
        seed_audio = np.array([], dtype=np.float32)

    print_err("seed_audio size*itemsize =", seed_audio.size * seed_audio.itemsize)

    temps = []
    for i in range(num_outs):
        temp_len_msg = read_msg(stdin, protocol.size_struct.size)
        temp_len = protocol.from_size_msg(temp_len_msg)
        
        temp_str_msg = read_msg(stdin, temp_len)
        temp_str = protocol.from_str_msg(temp_str_msg)

        temp = gen.check_temperature(temp_str)
        
        temps.append(temp)

    print_err("temps =", temps)

    # out_audios = [np.random.uniform(0.0, 1.0, out_len).astype(np.float32)]*num_outs
    out_audios = list(generate(state, out_sr, dur, temps, seed_audio))

    print_err("generated")
    
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_GENERATED))
    stdout.write(protocol.to_generated_msg(out_sr, len(out_audios), out_audios[0].size))
    for audio in out_audios:
       stdout.write(protocol.to_audio_msg(audio))
    stdout.flush()
        
handlers = {
    protocol.IN_TAG_GENERATE: handle_generate
}
