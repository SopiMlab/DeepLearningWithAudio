import os
import random
import struct
import sys
import tensorflow.compat.v1 as tf
import numpy as np
import pickle

from magenta.models.gansynth.lib import generate_util as gu

from sopilib import gansynth_protocol as protocol
from sopilib.utils import print_err, read_msg, suppress_stdout

def handle_rand_z(model, stdin, stdout, state):
    """
        Generates a given number of new Z coordinates.
    """
    count_msg = read_msg(stdin, protocol.count_struct.size)
    count = protocol.from_count_msg(count_msg)

    with suppress_stdout():
        zs = model.generate_z(count)
    
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_Z))
    stdout.write(protocol.to_count_msg(len(zs)))
    
    for z in zs:
        stdout.write(protocol.to_z_msg(z))
        
    stdout.flush()

def handle_load_ganspace_components(model, stdin, stdout, state):
    size_msg = read_msg(stdin, protocol.int_struct.size)
    size = protocol.from_int_msg(size_msg)
    msg = read_msg(stdin, size)
    file = msg.decode('utf-8')
    print_err("Opening components file '{}'".format(file))
    with open(file, "rb") as fp:
        state['ganspace_components'] = pickle.load(fp)
    print_err("Components file loaded.")

    component_count = len(state['ganspace_components']["comp"])
    state['ganspace_component_count'] = component_count
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_LOAD_COMPONENTS))
    stdout.write(protocol.to_count_msg(component_count))
    stdout.flush()

def handle_set_component_amplitudes(model, stdin, stdout, state):
    amplitudes = []
    for i in range(0, state['ganspace_component_count']):
        msg = read_msg(stdin, protocol.f64_struct.size)
        value = protocol.from_float_msg(msg)
        amplitudes.append(value)
    state['ganspace_component_amplitudes'] = amplitudes

def handle_slerp_z(model, stdin, stdout, state):
    slerp_z_msg = read_msg(stdin, protocol.slerp_z_struct.size)
    z0, z1, amount = protocol.from_slerp_z_msg(slerp_z_msg)

    z = gu.slerp(z0, z1, amount)

    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_Z))
    stdout.write(protocol.to_count_msg(1))
    stdout.write(protocol.to_z_msg(z))
    
    stdout.flush()
    
def handle_gen_audio(model, stdin, stdout, state):
    count_msg = read_msg(stdin, protocol.count_struct.size)
    count = protocol.from_count_msg(count_msg)
    
    pitches = []
    zs = []
    for i in range(count):
        gen_msg = read_msg(stdin, protocol.gen_audio_struct.size)
        
        pitch, z = protocol.from_gen_msg(gen_msg)
        
        pitches.append(pitch)
        zs.append(z)

    layer_offsets = {}
    if 'ganspace_component_amplitudes' in state:
        components = state['ganspace_components']['comp']
        std_devs = state['ganspace_components']['stdev']
        edits = state['ganspace_component_amplitudes']

        amounts = np.zeros(components.shape[:1], dtype=np.float32)
        amounts[:len(list(map(float, edits)))] = edits * std_devs

        scaled_directions = amounts.reshape(-1, 1, 1, 1) * components

        linear_combination = np.sum(scaled_directions, axis=0)
        linear_combination_batch = np.repeat(
            linear_combination.reshape(1, *linear_combination.shape),
            8,
            axis=0
        )


        layer_offsets[state['ganspace_components']['layer']] = linear_combination_batch

    z_arr = np.array(zs)
    try:
        with suppress_stdout():
            audios = model.generate_samples_from_z(z_arr, pitches, layer_offsets=layer_offsets)
    except KeyError as e:
        print_err("can't synthesize - model was not trained on pitch {}".format(e.args[0]))
        audios = []
        
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_AUDIO))
    stdout.write(protocol.to_count_msg(len(audios)))

    for audio in audios:
        stdout.write(protocol.to_audio_size_msg(audio.size * audio.itemsize))
        stdout.write(protocol.to_audio_msg(audio))

    stdout.flush()
    
def handle_synthesize_noz(model, stdin, stdout, state):
    print_err("handle_synthesize_noz")
    
    count_msg = read_msg(stdin, protocol.count_struct.size)
    count = protocol.from_count_msg(count_msg)
    
    pitches = []
    for i in range(count):
        gen_msg = read_msg(stdin, protocol.synthesize_noz_struct.size)
        
        pitch = protocol.from_synthesize_noz_msg(gen_msg)
        
        pitches.append(pitch)
        
    pca = state["ganspace_components"]
    edits = np.array(state["ganspace_component_amplitudes"], dtype=pca["stdev"].dtype)
    edits = np.repeat([edits], len(pitches), axis=0)
    
    try:
        with suppress_stdout():
            audios = model.generate_samples_from_edits(pitches, edits, pca)
    except KeyError as e:
        print_err("can't synthesize - model was not trained on pitch {}".format(e.args[0]))
        audios = []

    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_AUDIO))
    stdout.write(protocol.to_count_msg(len(audios)))

    for audio in audios:
        stdout.write(protocol.to_audio_size_msg(audio.size * audio.itemsize))
        stdout.write(protocol.to_audio_msg(audio))

    stdout.flush()
        
handlers = {
    protocol.IN_TAG_RAND_Z: handle_rand_z,
    protocol.IN_TAG_SLERP_Z: handle_slerp_z,
    protocol.IN_TAG_GEN_AUDIO: handle_gen_audio,
    protocol.IN_TAG_LOAD_COMPONENTS: handle_load_ganspace_components,
    protocol.IN_TAG_SET_COMPONENT_AMPLITUDES: handle_set_component_amplitudes,
    protocol.IN_TAG_SYNTHESIZE_NOZ: handle_synthesize_noz
}
