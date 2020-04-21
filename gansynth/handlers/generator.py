import os
import random
import struct
import sys

import numpy as np

from magenta.models.gansynth.lib import generate_util as gu

from sopilib import gansynth_protocol as protocol
from sopilib.utils import print_err, read_msg


def handle_rand_z(model, stdin, stdout):
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

def handle_slerp_z(model, stdin, stdout):
    slerp_z_msg = read_msg(stdin, protocol.slerp_z_struct.size)
    z0, z1, amount = protocol.from_slerp_z_msg(slerp_z_msg)

    z = gu.slerp(z0, z1, amount)

    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_Z))
    stdout.write(protocol.to_count_msg(1))
    stdout.write(protocol.to_z_msg(z))
    
    stdout.flush()
    
def handle_gen_audio(model, stdin, stdout):
    count_msg = read_msg(stdin, protocol.count_struct.size)
    count = protocol.from_count_msg(count_msg)
    
    pitches = []
    zs = []
    for i in range(count):
        gen_msg = read_msg(stdin, protocol.gen_audio_struct.size)
        
        pitch, z = protocol.from_gen_msg(gen_msg)
        
        pitches.append(pitch)
        zs.append(z)

    z_arr = np.array(zs)
    try:
        audios = model.generate_samples_from_z(z_arr, pitches)
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
    protocol.IN_TAG_GEN_AUDIO: handle_gen_audio
}
