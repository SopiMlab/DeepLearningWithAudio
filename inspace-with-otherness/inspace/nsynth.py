from __future__ import print_function

from functools import reduce
import json
import os
import sys

import numpy as np

print("loading nsynthplayer")

try:
    import pyext
    ext_class = pyext._class
except:
    print("failed to load pyext module")
    
    class ext_class(object):
        def _outlet(self, *args):
            print("_outlet{}".format(args))

try:
    import psyco
    psyco.full()
    print("Using JIT compilation")
except:
    # don't care
    pass
            
script_dir = os.path.dirname(os.path.realpath(__file__))

def load_settings(settings_path):
    with open(settings_path, "r") as f:
        return json.load(f)

def load_audio(audio_path):
    with open(audio_path, "rb") as f:
        return np.fromfile(f, dtype=np.int16)
    
# TODO: handle multiple instruments per corner
def extract_samples(audio, rows, cols, length, pitches):
    if sorted(pitches) != pitches:
        raise ValueError("pitches list is not sorted")
    
    n = rows * cols

    n_pitches = len(audio) // n // length
    #print("pitches={}".format(pitches))
    #print("len(audio)={} n_pitches={}".format(len(audio), n_pitches))

    if len(pitches) != n_pitches:
        raise ValueError("n_pitches does not match length of pitches list")

    samples = np.reshape(audio, (rows, cols, n_pitches, length))
    pitches_arr = np.array(pitches, dtype=np.uint8)
                
    return samples, pitches_arr

def extract_samples_from_file(audio_path, settings):
    rows = settings["nsynth"]["resolution"]
    cols = rows
    length = settings["nsynth"]["length"]
    pitches = settings["nsynth"]["pitches"]
        
    audio = load_audio(audio_path)
    
    return extract_samples(audio, rows, cols, length, pitches)

def offset(dims, indices):
    return sum(j*reduce(lambda x, y: x*y, dims[i+1:], 1) for i, j in enumerate(indices))

class loader(ext_class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1

    def load_1(self, audio_path, settings_path, buf_name):
        settings_path1 = os.path.join(script_dir, str(settings_path))
        audio_path1 = os.path.join(script_dir, str(audio_path))
        
        settings = load_settings(settings_path1)
        audio = load_audio(audio_path1)

        audio_f32 = audio.astype(np.float32) / 2**15
        buf = pyext.Buffer(buf_name)
        if len(buf) != len(audio_f32):
            buf.resize(len(audio_f32))

        buf[:] = audio_f32
        buf.dirty()

        rows = settings["nsynth"]["resolution"]
        cols = rows
        length = settings["nsynth"]["length"]
        sample_rate = settings["nsynth"]["sampleRate"]
        pitches = settings["nsynth"]["pitches"]
        
        self._outlet(1, "loaded", [rows, cols, length, sample_rate] + pitches)

class controller(ext_class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1

        # rows, cols, pitches, length
        self.dimensions = (0, 0, 0, 0)
        self.length = 0
        self.sample_rate = 16000
        self.pitches = np.array((), dtype=np.uint8)

        self.row = 0
        self.col = 0

        self.pitch = None
        self.notes = (
            7, 12, 10, 5, 9, 10,
            7, 12, 15, 14, 10, 5,
            0, 7, 3, 2, -2, -3,
            0, 7, 10, 9, 5, 3
        )
        self.note_ix = 0

    def _find_closest_pitch_i(self, pitch):
        i_r = np.searchsorted(self.pitches, pitch)

        if i_r == 0:
            return i_r

        if i_r == len(self.pitches):
            return i_r - 1
        
        pitch_r = self.pitches[i_r]

        if pitch_r == pitch:
            return i_r

        i_l = i_r - 1
        pitch_l = self.pitches[i_l]

        if pitch_l == pitch:
            return i_l

        diff_l = pitch - pitch_l
        diff_r = pitch_r - pitch

        return i_l if diff_l <= diff_r else i_r
        
    def loaded_1(self, rows, cols, length, sample_rate, *pitches):
        self.dimensions = (rows, cols, len(pitches), length)
        self.length = length
        self.sample_rate = sample_rate
        self.pitches = np.array(pitches, dtype=np.uint8)

    def position_rel_1(self, y, x):
        row = round(y * (self.dimensions[0] - 1))
        col = round(x * (self.dimensions[1] - 1))

        trig = row != self.row or col != self.col

        self.row = row
        self.col = col

        if trig:
            pitch = self.notes[self.note_ix]
            self.note_ix = (self.note_ix + 1) % len(self.notes)
            self.note_on_1(pitch)
        
    def position_1(self, row, col):
        self.row = row
        self.col = col

        pitch = self.notes[self.note_ix]
        self.note_ix = (self.note_ix + 1) % len(self.notes)
        self.note_on_1(pitch) 
        
    def note_on_1(self, pitch):
        closest_pitch_i = self._find_closest_pitch_i(pitch)
        closest_pitch = self.pitches[closest_pitch_i]
        rate = 2.0**((pitch - closest_pitch)/12.0)

        onset = offset(self.dimensions, (self.row, self.col, closest_pitch_i, 0))
        start = 0
        end = self.length - 1
        duration = float(self.length) / self.sample_rate * 1000 / rate

        #print("play", start, end, duration, onset)
        self._outlet(1, "play", start, end, duration, onset)

    def set_pitch_1(self, pitch):
        self.pitch = pitch
        
    def set_notes_1(self, *notes):
        self.notes = notes
        self.note_ix = 0

class player0(ext_class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1
        self.settings = None
        self.pitches = None
        self.samples = None

    def _dsp(self):
        if not self._arraysupport():
            print("No DSP support")
            return False
        
    def load_1(self, audio_path, settings_path):
        self.settings = load_settings(settings_path)
        self.samples, self.pitches = extract_samples_from_file(audio_path, self.settings)

    def note_on_1(self, pitch, vel):
        if self.samples == None:
            return
        
        max_pitch_i = self.pitches.size - 1
        pitch_insert_i = np.searchsorted(self.pitches, pitch)
        closest_pitch_i = min(max_pitch_i, pitch_insert_i)
        closest_pitch = self.pitches[closest_pitch_i]

        rate = 2.0**((pitch - closest_pitch)/12.0)

        #print("pitch =", pitch)
        #print("closest_pitch =", closest_pitch)
        #print("rate =", rate)
