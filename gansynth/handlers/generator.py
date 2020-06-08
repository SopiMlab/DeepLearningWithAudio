import os
import random
import struct
import sys
import tensorflow.compat.v1 as tf
import numpy as np
import pickle

from magenta.models.gansynth.lib import generate_util as gu

from sopilib import gansynth_protocol as protocol
from sopilib.utils import print_err, read_msg


def handle_rand_z(model, stdin, stdout, state):
    """
        Generates a given number of new Z coordinates.
    """
    count_msg = read_msg(stdin, protocol.count_struct.size)
    count = protocol.from_count_msg(count_msg)
    
    zs = model.generate_z(count)
    
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_Z))
    stdout.write(protocol.to_count_msg(len(zs)))
    
    for z in zs:
        stdout.write(protocol.to_z_msg(z))
        
    stdout.flush()

def handle_load_ganspace_components(model, stdin, stdout, state):
    msg = read_msg(stdin, protocol.load_ganspace_components_struct.size)
    file = protocol.from_load_ganspace_components_msg(msg)
    #with open(file, "r") as fp:
    #    state['ganspace_components'] = pickle.load(fp)
    l = 'conv1_2'
    state['ganspace_components'] = {
        "comp": [np.zeros(model.fake_offsets[l].shape.as_list(), np.float32)],
        "stdev": [np.zeros(model.fake_offsets[l].shape.as_list(), np.float32)],
        "var_ratio": [],
        "layer": l
    }
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
        offsets = np.zeros(np.shape(components[0]), np.float32)
        for i, v in enumerate(state['ganspace_component_amplitudes']):
            c = np.array(components[i])
            std_dev = np.array(std_devs[i])
            offsets += c * v * std_dev
        layer_offsets[state['ganspace_components']['layer']] = offsets

    z_arr = np.array(zs)
    try:
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

handlers = {
    protocol.IN_TAG_RAND_Z: handle_rand_z,
    protocol.IN_TAG_SLERP_Z: handle_slerp_z,
    protocol.IN_TAG_GEN_AUDIO: handle_gen_audio,
    protocol.IN_TAG_LOAD_COMPONENTS: handle_load_ganspace_components,
    protocol.IN_TAG_SET_COMPONENT_AMPLITUDES: handle_set_component_amplitudes
}
