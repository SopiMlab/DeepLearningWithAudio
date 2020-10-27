from __future__ import print_function
import sys
import os
import random
import sys
import math

import numpy as np
import scipy.io.wavfile as wavfile

from magenta.models.gansynth.lib import generate_util as gu

from sopilib import gansynth_protocol as protocol
from sopilib.utils import print_err, read_msg

def synthesize(model, zs, pitches):
    z_arr = np.array(zs)
    return model.generate_samples_from_z(z_arr, pitches)

def slerp(p0, p1, t):
  #Spherical linear interpolation.
  omega = np.arccos(np.dot(
      np.squeeze(p0/np.linalg.norm(p0)), np.squeeze(p1/np.linalg.norm(p1))))
  so = np.sin(omega)
  return np.sin((1.0-t)*omega) / so * p0 + np.sin(t*omega)/so * p1

def lerp(v0, v1, t):
  return (1 - t) * v0 + t * v1

def get_envelope(t_trim_start=0.0, t_attack=0.010, t_sustain=0.5, t_release=0.3, max_note_length=46000, sr=16000):
    """
        Creates an attack sustain release amplitude envelope.
        Modified version of GANSynth generator utils.
        Added option to trim sound from the start of the sample, 
        and made t_attack be counted into the total length of the envelope.


        sr = Sample Rate
    """
    i_trim_start = int(sr * t_trim_start)
    i_attack = int(sr * t_attack)
    i_sustain = int(sr * t_sustain)
    i_release = int(sr * t_release)
    i_tot = i_trim_start + i_attack + i_sustain + i_release
    
    i_tot_sec = math.floor((i_tot / sr) * 100)/100.0
    max_len = math.floor((max_note_length / sr) * 100)/100.0

    if i_tot_sec > max_len:
        raise ValueError('Cannot generate evelope longer than ' + str(max_len) + 
                         '. Tried to generate len = ' + str(i_tot))

    envelope = np.ones(i_tot)
    # Linear attack
    if i_trim_start > 0:
        envelope[:i_trim_start] = 0
    envelope[i_trim_start:i_trim_start+i_attack] = np.linspace(0.0, 1.0, i_attack)
    # Linear release
    envelope[i_trim_start+i_attack+i_sustain:i_tot] = np.linspace(1.0, 0.0, i_release)
    return envelope

def interpolate_notes(notes, pitches, steps, use_linear = False):
    result_notes = []
    result_pitches = []
    if len(notes) >= 2:
        for i in range(0, len(notes) - 1):
            start_note = notes[i]
            start_pitch = pitches[i]
            end_note = notes[i + 1]
            end_pitch = pitches[i + 1]
            
            result_notes.append(start_note)
            result_pitches.append(start_pitch)

            for step in range(1, steps + 1):
                interp = step / float(steps)
                if use_linear:
                    result_notes.append([lerp(note, end_note[i], interp) for (i, note) in enumerate(start_note)])
                else:
                    result_notes.append(slerp(start_note, end_note, interp))
                result_pitches.append(math.floor(lerp(start_pitch, end_pitch, interp)))
        
        result_notes.append(notes[-1])
        result_pitches.append(result_pitches[-1])
    else:
        result_notes.append(notes[0])
        result_pitches.append(pitches[0])

    return (result_notes, result_pitches)

def combine_notes(audio_notes, 
        vel = 0.5,
        sustain = 0.5,
        attack = 0.5,
        release = 0.5,
        start_trim = 0.1,
        spacing = 0.5,
        max_note_length = 46000,
        sr=16000):
    """Combine audio from multiple notes into a single audio clip.
    Args:
    audio_notes: Array of audio [n_notes, audio_samples].
    sr: Integer, sample rate.
    Returns:
    audio_clip: Array of combined audio clip [audio_samples]
    """
    MAX_VELOCITY = 127.0
    n_notes = len(audio_notes)
    
    clip_length = spacing * (n_notes + 1) + (max_note_length / sr)
    audio_clip = np.zeros(int(clip_length) * sr)

    

    for i in range(n_notes):
        # Generate an amplitude envelope
        envelope = get_envelope(start_trim, attack, sustain, release, max_note_length=max_note_length, sr=sr)
        length = len(envelope)
        audio_note = audio_notes[i, :length] * envelope
        # Normalize
        audio_note /= audio_note.max()
        audio_note *= (vel / MAX_VELOCITY)
        # Add to clip buffer
        clip_start = int(spacing * i * sr)
        clip_end = clip_start + length
        audio_clip[clip_start:clip_end] += audio_note

    # Normalize
    audio_clip /= audio_clip.max()
    audio_clip /= 2.0
    return audio_clip


def handle_hallucinate(model, stdin, stdout, state):
    max_note_length = model.config['audio_length']
    sample_rate = model.config['sample_rate']

    hallucinate_msg = read_msg(stdin, protocol.hallucinate_struct.size)
    args = protocol.from_hallucinate_msg(hallucinate_msg)
    note_count, interpolation_steps, spacing, start_trim, attack, sustain, release = args

    print_err("note_count = {} interpolation_steps = {}, spacing = {}s, start_trim = {}s, attack = {}s, sustain = {}s, release = {}s".format(*args))

    initial_notes = model.generate_z(note_count)
    initial_piches = np.array([32] * len(initial_notes)) # np.floor(30 + np.random.rand(len(initial_notes)) * 30)
    final_notes, final_pitches = interpolate_notes(initial_notes, initial_piches, interpolation_steps)

    audios = synthesize(model, final_notes, final_pitches)
    final_audio = combine_notes(audios, spacing = spacing, start_trim = start_trim, attack = attack, sustain = sustain, release = release, max_note_length=max_note_length, sr=sample_rate)

    final_audio = final_audio.astype('float32')

    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_AUDIO))
    stdout.write(protocol.to_audio_size_msg(final_audio.size * final_audio.itemsize))
    stdout.write(protocol.to_audio_msg(final_audio))
    stdout.flush()

def interpolate_edits(seq, step_count):
    last_i = len(seq) - 1
    for i, edits0 in enumerate(seq):
        yield edits0
        if i < last_i:
            edits1 = seq[i+1]
            for j in range(1, step_count):
                x = j/step_count
                yield lerp(edits0, edits1, x)

def handle_hallucinate_noz(model, stdin, stdout, state):
    max_note_length = model.config['audio_length']
    sample_rate = model.config['sample_rate']

    pca = state["ganspace_components"]
    stdevs = pca["stdev"]
    layer_dtype = stdevs.dtype

    hallucinate_msg = read_msg(stdin, protocol.hallucinate_struct.size)
    step_count, interpolation_steps, spacing, start_trim, attack, sustain, release = protocol.from_hallucinate_msg(hallucinate_msg)
    
    edit_count_msg = read_msg(stdin, protocol.count_struct.size)
    edit_count = protocol.from_count_msg(edit_count_msg)

    pitch = min(model.pitch_counts.keys())
    
    steps = []
    for i in range(step_count):
        edits = []
        for j in range(edit_count):
            edit_msg = read_msg(stdin, protocol.f64_struct.size)
            edit = protocol.from_f64_msg(edit_msg)
            
            edits.append(edit)

        steps.append(np.array(edits, dtype=layer_dtype))
    
    steps = list(interpolate_edits(steps, interpolation_steps))

    layer_steps = np.array(list(map(lambda edits: model.make_edits_layer(pca, edits), steps)), dtype=layer_dtype)
    pitch_steps = np.repeat([pitch], len(steps))

    audios = model.generate_samples_from_layers({pca["layer"]: layer_steps}, pitch_steps)

    final_audio = combine_notes(audios, spacing = spacing, start_trim = start_trim, attack = attack, sustain = sustain, release = release, max_note_length=max_note_length, sr=sample_rate)
    final_audio = final_audio.astype("float32")
        
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_AUDIO))
    stdout.write(protocol.to_audio_size_msg(final_audio.size * final_audio.itemsize))
    stdout.write(protocol.to_audio_msg(final_audio))
    stdout.flush()

    
handlers = {
    protocol.IN_TAG_HALLUCINATE: handle_hallucinate,
    protocol.IN_TAG_HALLUCINATE_NOZ: handle_hallucinate_noz
}
