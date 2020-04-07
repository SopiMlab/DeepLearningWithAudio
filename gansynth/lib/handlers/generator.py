from .. import communication_struct as gss
from ..utils import read_msg

import os
import random
import struct
import sys

import numpy as np

def handle_rand_z(model, stdin, stdout):
    """
        Generates a given number of new Z coordinates.
    """
    count_msg = read_msg(stdin, gss.count_struct.size)
    count = gss.from_count_msg(count_msg)
    
    zs = model.generate_z(count)
    
    stdout.write(gss.to_tag_msg(gss.OUT_TAG_Z))
    stdout.write(gss.to_count_msg(len(zs)))
    
    for z in zs:
        stdout.write(gss.to_z_msg(z))
        
    stdout.flush()

def handle_gen_audio(model, stdin, stdout):
    count_msg = read_msg(stdin, gss.count_struct.size)
    count = gss.from_count_msg(count_msg)
    
    pitches = []
    zs = []
    for i in range(count):
        gen_msg = read_msg(stdin, gss.gen_audio_struct.size)
        
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

    stdout.flush()

handlers = {
    gss.IN_TAG_RAND_Z: handle_rand_z,
    gss.IN_TAG_GEN_AUDIO: handle_gen_audio
}
