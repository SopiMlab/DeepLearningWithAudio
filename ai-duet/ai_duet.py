# based on https://github.com/googlecreativelab/aiexperiments-ai-duet

from __future__ import print_function

print("loading ai_duet")
import sys    

import os
import Queue
import random
import threading
import time

import magenta
from magenta.models.melody_rnn import melody_rnn_config_flags
from magenta.models.melody_rnn import melody_rnn_model
from magenta.models.melody_rnn import melody_rnn_sequence_generator
from magenta.protobuf import generator_pb2
from magenta.protobuf import music_pb2
import monotonic
import pretty_midi

try:
    import pyext
    ext_class = pyext._class
except:
    print("failed to load pyext module")
    
    class ext_class(object):
        def _outlet(self, *args):
            print("_outlet{}".format(args))

script_dir = os.path.dirname(os.path.realpath(__file__))

test_notes = [(0.5, 32, 100), (0.6, 33, 50), (0.7, 33, 0), (0.8, 32, 0)]

def notes_to_midi(notes, t0 = 0.0):    
    midi = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(0)

    # add notes to instrument
    # a note is added only after a note-on and a corresponding note-off
    notes_on = {}
    for t_raw, pitch, vel in notes:
        t = t_raw - t0
        
        if vel > 0:
            notes_on[pitch] = (t, vel)
        elif pitch in notes_on:
            t_on, vel_on = notes_on[pitch]
            note = pretty_midi.Note(vel_on, pitch, t_on, t)
            inst.notes.append(note)

    # sort notes by start time
    inst.notes.sort(key = lambda n: n.start)
            
    midi.instruments.append(inst)

    return midi

def midi_to_notes(midi):
    notes = []

    # split notes into on and off notes
    for midi_note in midi.instruments[0].notes:
        notes.append((midi_note.start, midi_note.pitch, midi_note.velocity))
        notes.append((midi_note.end, midi_note.pitch, 0))

    # sort notes by time
    notes.sort(key = lambda n: n[0])

    return notes

def steps_to_seconds(steps, qpm):
    return steps * 60.0 / qpm / 4.0

class melody_rnn(ext_class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1

        self.generator = None
        self.notes = []
        self.t0 = 0

        self.queue = Queue.Queue()
        self.play_thread = threading.Thread(target = self._keep_playing)
        self.play_thread.start()

    def _make_play_note(self, pitch, vel, is_last):
        def _play_note():
            self._outlet(1, "note", pitch, vel)
            if is_last:
                self._outlet(1, "played")

        return _play_note
        
    def _keep_playing(self):
        pending_timer = None
        while True:
            # wait for any previous sequence to finish

            if pending_timer:
                pending_timer.join(timeout = 1.0)

                if self._shouldexit:
                    return

                if pending_timer.is_alive():
                    continue
                else:
                    pending_timer = None

            # get notes from queue
            
            try:
                notes = self.queue.get(timeout = 1.0)
            except Queue.Empty:
                notes = None

            if self._shouldexit:
                return

            if notes == None:
                # queue was empty
                continue

            if not notes:
                # got empty notes list
                self._outlet(1, "played")
                continue
            
            # schedule note timers
            
            last_i = len(notes) - 1
            timers = []
            for i, (t, pitch, vel) in enumerate(notes):
                is_last = i == last_i
                play_note = self._make_play_note(pitch, vel, is_last)
                timer = threading.Timer(t, play_note)
                timers.append(timer)

                if is_last:
                    pending_timer = timer

            for timer in timers:
                timer.start()                
        
    def load_1(self, bundle_name):
        bundle_name = str(bundle_name)
        config = magenta.models.melody_rnn.melody_rnn_model.default_configs[bundle_name]
        bundle_file = magenta.music.read_bundle_file(os.path.join(script_dir, bundle_name+'.mag'))
        steps_per_quarter = 4

        self.generator = melody_rnn_sequence_generator.MelodyRnnSequenceGenerator(
            model = melody_rnn_model.MelodyRnnModel(config),
            details = config.details,
            steps_per_quarter = steps_per_quarter,
            bundle = bundle_file
        )

        self._outlet(1, "loaded")

    def note_1(self, pitch, vel):
        t = monotonic.time.time()
        if len(self.notes) == 0:
            self.t0 = t
        
        note = (t, pitch, vel)
        self.notes.append(note)

    def clear_1(self):
        del self.notes[:]

    def state_1(self):
        print("notes =", self.notes)
        print("t0 =", self.t0)
        
    def generate_1(self, duration):        
        # prepare the note sequence
        
        midi = notes_to_midi(self.notes, self.t0)
        primer_seq = magenta.music.midi_io.midi_to_note_sequence(midi)

        # predict the tempo

        if len(primer_seq.notes) > 4:
            estimated_tempo = midi.estimate_tempo()
            if estimated_tempo > 240:
                qpm = estimated_tempo / 2
            else:
                qpm = estimated_tempo
        else:
            qpm = 120
        
        primer_seq.tempos[0].qpm = qpm

        # generate
        
        gen_options = generator_pb2.GeneratorOptions()
        last_end_time = max(n.end_time for n in primer_seq.notes) if primer_seq.notes else 0
        gen_start_time = last_end_time + steps_to_seconds(1, qpm)
        gen_end_time = gen_start_time + duration
        gen_options.generate_sections.add(start_time = gen_start_time, end_time = gen_end_time)

        gen_seq = self.generator.generate(primer_seq, gen_options)
        gen_midi = magenta.music.midi_io.note_sequence_to_pretty_midi(gen_seq)

        # the primer sequence is included in the generated data, so strip it

        new_notes = []
        for note in gen_midi.instruments[0].notes:
            if note.start >= gen_start_time:
                new_note = pretty_midi.Note(
                    note.velocity,
                    note.pitch,
                    note.start - gen_start_time,
                    note.end - gen_start_time
                )
                new_notes.append(new_note)

        gen_midi.instruments[0].notes = new_notes
        gen_notes = midi_to_notes(gen_midi)

        # add the new notes to the play queue
        
        self.queue.put(gen_notes)
        
    def _anything_1(self, *args):
        print("unhandled input:", args)

"""
mrnn = melody_rnn()
mrnn.load_1("attention_rnn")
mrnn.note_1(32, 100)
time.sleep(0.1)
mrnn.note_1(35, 100)
time.sleep(0.1)
mrnn.note_1(37, 100)
time.sleep(0.1)
mrnn.note_1(32, 0)
time.sleep(0.1)
mrnn.note_1(35, 0)
time.sleep(0.1)
mrnn.note_1(37, 0)
mrnn.generate_1()
"""
