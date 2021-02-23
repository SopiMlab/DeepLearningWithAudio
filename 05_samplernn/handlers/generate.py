import argparse
import os
import time

import numpy as np
from samplernn import (dequantize, quantize)
from samplernn_scripts import generate as gen
import tensorflow as tf

import sopilib.samplernn_protocol as protocol
from sopilib.utils import print_err, read_msg

NUM_FRAMES_TO_PRINT = 4

def generate(state, sample_rate, num_samples, temperature, seed):
    print_err("num_samples =", num_samples)
    print_err("state =", state)
    config = state.config
    num_seqs = state.num_seqs
    model = state.model

    seed_offset = 0
    
    q_type = model.q_type
    q_levels = model.q_levels
    q_zero = q_levels // 2
    print_err("temperature 0 =", temperature)
    temperature = gen.get_temperature(temperature, num_seqs)
    print_err("temperature 1 =", temperature)
    # Precompute sample sequences, initialised to q_zero.
    samples = []
    init_samples = np.full((model.batch_size, model.big_frame_size, 1), q_zero)
    # Set seed if provided.
    if seed:
        # seed_audio = gen.load_seed_audio(seed, seed_offset, model.big_frame_size)
        seed_audio = seed
        seed_audio = tf.convert_to_tensor(seed_audio)
        init_samples[:, :model.big_frame_size, :] = quantize(seed_audio, q_type, q_levels)
    init_samples = tf.constant(init_samples, dtype=tf.int32)
    samples.append(init_samples)
    print_progress_every = NUM_FRAMES_TO_PRINT * model.big_frame_size
    start_time = time.time()
    for i in range(0, num_samples // model.big_frame_size):
        t = i * model.big_frame_size
        # Generate samples
        frame_samples = model(samples[i], training=False, temperature=temperature)
        samples.append(frame_samples)
        # Monitor progress
        if t % print_progress_every == 0:
            end = min(t + print_progress_every, num_samples)
            step_dur = time.time() - start_time
            print_err(f'Generated samples {t+1} - {end} of {num_samples} (time elapsed: {step_dur:.3f} seconds)')
    samples = tf.concat(samples, axis=1)
    samples = samples[:, model.big_frame_size:, :]
    for i in range(model.batch_size):
        seq = np.reshape(samples[i], (-1, 1))[model.big_frame_size :].tolist()
        audio = dequantize(seq, q_type, q_levels)
        yield audio.numpy()

def handle_generate(state):
    stdin = state.stdin
    stdout = state.stdout
    model = state.model
    
    generate_msg = read_msg(stdin, protocol.generate_struct.size)
    seed_sr, out_sr, num_outs, out_len, seed_len = protocol.from_generate_msg(generate_msg)

    print_err("seed_sr =", seed_sr)
    print_err("out_sr =", out_sr)
    print_err("num_outs =", num_outs)
    print_err("out_len =", out_len)
    print_err("seed_len =", seed_len)

    temps = []
    for i in range(num_outs):
        temp_msg = read_msg(stdin, protocol.f32_struct.size)
        temps.append(protocol.from_f32_msg(temp_msg))

    print_err("temps =", temps)

    if seed_len > 0:
        seed_msg = read_msg(stdin, seed_len * protocol.f32_struct.size)
        seed_audio = protocol.from_audio_msg(seed_msg)
    else:
        seed_audio = np.array([], dtype=np.float32)

    print_err("seed_audio size*itemsize =", seed_audio.size * seed_audio.itemsize)

    # out_audios = [np.random.uniform(0.0, 1.0, out_len).astype(np.float32)]*num_outs
    out_audios = list(generate(state, out_sr, out_len, temps, seed_audio))

    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_GENERATED))
    stdout.write(protocol.to_generated_msg(out_sr, len(out_audios), out_audios[0].size))
    for audio in out_audios:
       stdout.write(protocol.to_audio_msg(audio))
    stdout.flush()
        
handlers = {
    protocol.IN_TAG_GENERATE: handle_generate
}
