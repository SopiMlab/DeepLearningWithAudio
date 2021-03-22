from __future__ import print_function

print("loading gansynth")
import sys

try:
    import pyext
except:
    print("ERROR: This script must be loaded by the PD/Max pyext external")

import math
import os
import random
import re
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np

import sopilib.gansynth_protocol as protocol
from sopilib.utils import print_err, sopimagenta_path

class gansynth(pyext._class):
    def __init__(self, out_buf_name, redundancy=0, batch_size=8, sample_rate=16000, gen_dur=4):
        self._inlets = 1
        self._outlets = 1
        self._proc = None
        self._stderr_printer = None
        self.ganspace_components_amplitudes_buffer_name = None

        self.out_buf_name = out_buf_name
        self.redundancy = redundancy
        self.batch_size = batch_size
        self.sample_rate = sample_rate
        self.gen_dur = gen_dur
        self.out_slots = [False] * self._num_out_slots() # False = free, True = used
        self.skipped = False
        self.last_synth_dur = 0.0
        
        # DEBUG
        sines = [440*2**(i/12) for i in [0,2,4,5,7,9,11,12]]
        self.sines = [np.array([0.5 * math.sin(i/44100.0*freq*2*math.pi) for i in range(self._out_slot_len())], dtype=np.float32) for freq in sines]
        self.sine_i = 0
        # /DEBUG
        
    def load_1(self, ckpt_dir):
        if self._proc != None:
            self.unload_1()

        out_buf_len = self._out_slot_len() * self._num_out_slots()
        print(f"resizing output buffer to {out_buf_len}")
        print(f"sample_rate={self.sample_rate}, gen_dur={self.gen_dur}, batch_size={self.batch_size}, redundancy={self.redundancy}")
        out_buf = pyext.Buffer(self.out_buf_name)
        out_buf.resize(out_buf_len)
        self._outlet(1, "slots", [self.redundancy, self.batch_size, self.sample_rate, self.gen_dur])
        
        python = sys.executable
        gen_script = sopimagenta_path("gansynth_worker")
        ckpt_dir = os.path.join(self._canvas_dir, str(ckpt_dir))

        print("starting gansynth_worker process, this may take a while", file=sys.stderr)

        self._proc = subprocess.Popen(
            (python, gen_script, ckpt_dir, str(self.batch_size)),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        self._stderr_printer = threading.Thread(target = self._keep_printing_stderr)
        self._stderr_printer.start()
        
        self._read_tag(protocol.OUT_TAG_INIT)
        
        info_msg = self._read(protocol.init_struct.size)
        audio_length, sample_rate = protocol.from_info_msg(info_msg)

        print("gansynth_worker is ready", file=sys.stderr)
        self._outlet(1, ["loaded", audio_length, sample_rate])

    def unload_1(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
            self._stderr_printer = None
        else:
            print("no gansynth_worker process is running", file=sys.stderr)

        self._outlet(1, "unloaded")

    def _num_out_slots(self):
        return self.batch_size * (1 + self.redundancy)

    def _out_slot_len(self):
        return self.sample_rate * self.gen_dur
    
    def _out_slot_start(self, i):
        return i * self._out_slot_len()

    def _free_out_slots(self, n):
        free_slots = []
        for i, used in enumerate(self.out_slots):
            if not self.out_slots[i]:
                free_slots.append(i)
            if len(free_slots) >= n:
                break

        # print(f"_free_out_slots: n={n}, out_slots={self.out_slots}, free_slots={free_slots}")
        if len(free_slots) < n:
            return None
            
        return free_slots
    
    def _keep_printing_stderr(self):
        while True:
            line = self._proc.stderr.readline()
            
            if not line:
                break

            sys.stderr.write("[gansynth_worker] ")
            sys.stderr.write(line.decode("utf-8"))
            sys.stderr.flush()
        
    def _write_msg(self, tag, *msgs):
        tag_msg = protocol.to_tag_msg(tag)
        self._proc.stdin.write(tag_msg)
        for msg in msgs:
            self._proc.stdin.write(msg)
        self._proc.stdin.flush()

    def _read(self, n):
        data = self._proc.stdout.read(n)
        return data
        
    def _read_tag(self, expected_tag):
        tag_msg = self._read(protocol.tag_struct.size)
        tag = protocol.from_tag_msg(tag_msg)

        if tag != expected_tag:
            raise ValueError("expected tag {}, got {}".format(expected_tag, tag))

        # based on http://blog.marmakoide.org/?p=1
    def _sphere_spread(self, r, n, center): 
        golden_angle = np.pi * (3 - np.sqrt(5))
        theta = golden_angle * np.arange(n)
        z = np.linspace(1 - 1.0 / n, 1.0 / n - 1, n)
        radius = np.sqrt(1 - z * z)
 
        points = np.zeros((n, 3))
        points[:,0] = center[0] + r * radius * np.cos(theta)
        points[:,1] = center[1] + r * radius * np.sin(theta)
        points[:,2] = center[2] + r * z
        
        return points
        
    def load_ganspace_components_1(self, ganspace_components_file, component_amplitudes_buff_name):
        ganspace_components_file = os.path.join(
            self._canvas_dir,
            str(ganspace_components_file)
        )

        print("Loading GANSpace components...", file=sys.stderr)

        size_msg = protocol.to_int_msg(len(ganspace_components_file))
        components_msg = ganspace_components_file.encode('utf-8')

        self._write_msg(protocol.IN_TAG_LOAD_COMPONENTS, size_msg, components_msg)
        self._read_tag(protocol.OUT_TAG_LOAD_COMPONENTS)
        count_msg = self._read(protocol.count_struct.size)
        component_count = protocol.from_count_msg(count_msg)

        self.ganspace_components_amplitudes_buffer_name = component_amplitudes_buff_name

        buf = pyext.Buffer(component_amplitudes_buff_name)
        buf.resize(component_count)
        buf.dirty()

        print("GANSpace components loaded!", file=sys.stderr)

        self._outlet(1, "loaded_pca")

    def randomize_z_1(self, *buf_names):
        if not self._proc:
            raise Exception("can't randomize z - no gansynth_worker process is running")

        in_count = len(buf_names)

        if in_count == 0:
            raise ValueError("no buffer name(s) specified")
        
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_RAND_Z, in_count_msg)
        
        self._read_tag(protocol.OUT_TAG_Z)

        out_count_msg = self._read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        assert out_count == in_count

        for buf_name in buf_names:
            z_msg = self._read(protocol.z_struct.size)
            z = protocol.from_z_msg(z_msg)

            z32 = z.astype(np.float32)
        
            buf = pyext.Buffer(buf_name)
            if len(buf) != len(z32):
                buf.resize(len(z32))

            buf[:] = z32
            buf.dirty()

        self._outlet(1, "randomized")

    def slerp_z_1(self, z0_name, z1_name, z_dst_name, amount):
        if not self._proc:
            raise Exception("can't slerp - no gansynth_worker process is running")

        z0_buf = pyext.Buffer(z0_name)
        z1_buf = pyext.Buffer(z1_name)
        z_dst_buf = pyext.Buffer(z_dst_name)

        z0_f64 = np.array(z0_buf, dtype=np.float64)
        z1_f64 = np.array(z1_buf, dtype=np.float64)
        
        self._write_msg(protocol.IN_TAG_SLERP_Z, protocol.to_slerp_z_msg(z0_f64, z1_f64, amount))

        self._read_tag(protocol.OUT_TAG_Z)

        out_count_msg = self._read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)

        assert out_count == 1

        z_msg = self._read(protocol.z_struct.size)
        z = protocol.from_z_msg(z_msg)

        z32 = z.astype(np.float32)

        if len(z_dst_buf) != len(z32):
            z_dst_buf.resize(len(z32))
        
        z_dst_buf[:] = z32
        z_dst_buf.dirty()

        self._outlet(1, "slerped")

    def synthesize_1(self, *args):
        if not self._proc:
            raise Exception("can't synthesize - no gansynth_worker process is running")
        
        arg_count = len(args)
        
        if arg_count == 0 or arg_count % 3 != 0:
            raise ValueError("invalid number of arguments ({}), should be a multiple of 3: synthesize z1 audio1 pitch1 [z2 audio2 pitch2 ...]".format(arg_count))

        if self.ganspace_components_amplitudes_buffer_name:
            component_buff = pyext.Buffer(self.ganspace_components_amplitudes_buffer_name)
            components = np.array(component_buff, dtype=np.float64)
            component_msgs = []
            for value in components:
                component_msgs.append(protocol.to_float_msg(value))
            self._write_msg(protocol.IN_TAG_SET_COMPONENT_AMPLITUDES, *component_msgs)


        gen_msgs = []
        audio_buf_names = []
        for i in range(0, arg_count, 3):
            z_buf_name, audio_buf_name, pitch = args[i:i+3]

            z32_buf = pyext.Buffer(z_buf_name)
            z = np.array(z32_buf, dtype=np.float64)
            
            gen_msgs.append(protocol.to_gen_msg(pitch, z))
            audio_buf_names.append(audio_buf_name)
            
        in_count = len(gen_msgs)
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_GEN_AUDIO, in_count_msg, *gen_msgs)
                
        self._read_tag(protocol.OUT_TAG_AUDIO)

        out_count_msg = self._read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        if out_count == 0:
            return

        assert out_count == in_count

        for audio_buf_name in audio_buf_names:
            audio_size_msg = self._read(protocol.audio_size_struct.size)
            audio_size = protocol.from_audio_size_msg(audio_size_msg)

            audio_msg = self._read(audio_size)
            audio_note = protocol.from_audio_msg(audio_msg)

            audio_buf = pyext.Buffer(audio_buf_name)
            if len(audio_buf) != len(audio_note):
                audio_buf.resize(len(audio_note))

            audio_buf[:] = audio_note
            audio_buf.dirty()
        
        self._outlet(1, "synthesized", *audio_buf_names)

    def synthesize_spread_1(self, *args):
        edits = []
        pitch = 0
        spread_radius = 0
        part = 0
        for arg in args:
            if str(arg) == "--":
                part += 1
            elif part == 0:
                edits.append(arg)
            elif part == 1:
                pitch = arg
                part += 1
            elif part == 2:
                spread_radius = arg
                part += 1
            else:
                raise ValueError("invalid syntax, should be: edit1 edit2 edit3 -- pitch spread_radius")

        while len(edits) < 3:
            edits.append(0)

        if len(edits) > 3:
            raise ValueError("more than 3 edits not supported")

        spread = self._sphere_spread(spread_radius, self.batch_size, edits)

        args1 = []
        for spread_edits in spread:
            if args1:
                args1.append("--")
            args1.append(pitch)
            args1.extend(spread_edits)
            
        self.synthesize_noz_1(*args1)
        
    # expected format: synthesize_noz pitch1 [edit1_1 edit1_2 ...] -- pitch2 [edit2_1 edit2_2 ...] -- [...]
    def synthesize_noz_1(self, *args):
        if not self._proc:
            raise Exception("can't synthesize - no gansynth_worker process is running")

        # parse the input
        
        init_sound = lambda: SimpleNamespace(pitch=None, edits=[], slot=None)
        
        sounds = [init_sound()]
        i = 0
        for arg in args:
            if str(arg) == "--":
                sounds.append(init_sound())
                i = 0
            else:
                if i == 0:
                    sounds[-1].pitch = arg
                else:
                    sounds[-1].edits.append(arg)

                i += 1
                
        # validate input and build synthesize messages
        
        synth_msgs = []
        for sound in sounds:
            if None in [sound.pitch]:
                raise ValueError("invalid syntax, should be: synthesize_noz pitch1 [edit1_1 edit1_2 ...] [-- pitch2 [edit2_1 edit2_2 ...]] [-- ...")

            synth_msgs.append(protocol.to_synthesize_noz_msg(sound.pitch, len(sound.edits)))
            for edit in sound.edits:
                synth_msgs.append(protocol.to_f64_msg(edit))

        num_sounds = len(sounds)
        if num_sounds != self.batch_size:
            raise ValueError(f"number of sounds ({num_sounds}) does not match batch size ({self.batch_size})") 

        # check that there are enough free slots

        synth_slots = self._free_out_slots(num_sounds)
        if synth_slots == None:
            if not self.skipped:
                print("skipping synthesis: not enough free slots")
                time.sleep(self.last_synth_dur)
            self.skipped = True
            self._outlet(1, "synthesis_skipped")
            return

        self.skipped = False
        
        for sound, slot in zip(sounds, synth_slots):
            sound.slot = slot
        
        # write synthesize messages
        
        in_count = len(sounds)
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_SYNTHESIZE_NOZ, in_count_msg, *synth_msgs)
        
        # wait for output

        # DEBUG
        # time.sleep(0.4)
        # /DEBUG

        t0 = time.time()
        self._read_tag(protocol.OUT_TAG_AUDIO)
        t1 = time.time()
        self.last_synth_dur = t1 - t0

        out_count_msg = self._read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        assert out_count == in_count

        if out_count == 0:
            return

        out_buf = pyext.Buffer(self.out_buf_name)
        slot_len = self._out_slot_len()
        synthesized_slots = []
        # DEBUG
        # /DEBUG
        for i, sound in enumerate(sounds):
            audio_size_msg = self._read(protocol.audio_size_struct.size)
            audio_size = protocol.from_audio_size_msg(audio_size_msg)

            audio_msg = self._read(audio_size)
            audio_note = protocol.from_audio_msg(audio_msg)
            
            slot_start = self._out_slot_start(sound.slot)
            slot_stop = slot_start + slot_len
            self.out_slots[sound.slot] = True
            # print(f"sound {i} -> slot {sound.slot} ({slot_start}:{slot_stop})")
            assert len(audio_note) == slot_len
            out_buf[slot_start:slot_stop] = audio_note

            # DEBUG
            # out_buf[slot_start:slot_stop] = self.sines[sound.slot]
            # self.sine_i = (self.sine_i + 1) % len(self.sines)
            # /DEBUG
            
            synthesized_slots.append(sound.slot)
            
        out_buf.dirty()

        for i, slot in enumerate(synthesized_slots):
            msg = ["granular", f"grain{i+1}", "slot", slot]
            # print(f"out: {msg}")
            self._outlet(1, *msg)
        # print("----")
        self._outlet(1, "synthesized")

    def slot_unused_1(self, slot):
        # print(f"slot_unused {slot}")
        self.out_slots[slot] = False
        
    def hallucinate_1(self, *args):
        if not self._proc:
            raise Exception("can't synthesize - load a checkpoint first")

        arg_count = len(args)
        if arg_count < 3 or arg_count > 8:
            raise ValueError("invalid number of arguments ({}), should be one: hallucinate buffer_name note_count interpolation_steps".format(arg_count))

        audio_buf_name = args[0]
        note_count = int(args[1])
        interpolation_steps = int(args[2])
        rest = list(map(float, args[3:len(args)]))

        self._write_msg(protocol.IN_TAG_HALLUCINATE, protocol.to_hallucinate_msg(note_count, interpolation_steps, *rest))

        self._read_tag(protocol.OUT_TAG_AUDIO)

        audio_size_msg = self._read(protocol.audio_size_struct.size)
        audio_size = protocol.from_audio_size_msg(audio_size_msg)

        audio_msg = self._read(audio_size)
        audio_note = protocol.from_audio_msg(audio_msg)

        audio_buf = pyext.Buffer(audio_buf_name)
        if len(audio_buf) != len(audio_note):
            audio_buf.resize(len(audio_note))

        audio_buf[:] = audio_note
        audio_buf.dirty()
        
        self._outlet(1, ["hallucinated", audio_size])
