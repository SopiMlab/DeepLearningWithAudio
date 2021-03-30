from __future__ import print_function

try:
    import pyext
except:
    print("ERROR: This script must be loaded by the PD/Max pyext external")

import os
import random
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np

import sopilib.gansynth_protocol as protocol
from sopilib.utils import print_err, sopimagenta_path

script_dir = os.path.dirname(os.path.realpath(__file__))

def to_z32(z):
    return z.astype(np.float32)

def from_z32(z32):
    return z.astype(np.float64)

def save_z_buf(z_name, path):
    z_buf = pyext.Buffer(z_name)
    z = from_z32(z_buf)

    base, ext = os.path.splitext(path)
    if not ext:
        ext = ".npy"
    path_fixed = base + ext

    print_err("save: " + path_fixed)
        
    #np.save(z, path_fixed)

class halluseq(pyext._class):
    def __init__(self, edits_buf_name, *args):
        self._inlets = 1
        self._outlets = 1
        self._edits_buf_name = edits_buf_name
        self._component_count = None
        self._proc = None
        self._stderr_printer = None
        self._steps = []
        self._step_ix = 0
        self._steps.append(self._new_step())
        self._interp_steps = 1
        self._sample_spacing = 0.2
        self._start_trim = 0.0
        self._attack = 0.5
        self._sustain = 0.5
        self._release = 0.5
        
    def load_1(self, ckpt_dir, batch_size=1):
        if self._proc != None:
            self.unload_1()
            
        python = sys.executable
        worker_script = sopimagenta_path("gansynth_worker")
        ckpt_dir = os.path.join(self._canvas_dir, str(ckpt_dir))

        print_err("starting gansynth_worker process, this may take a while")

        self._proc = subprocess.Popen(
            (python, worker_script, ckpt_dir, str(batch_size)),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        self._stderr_printer = threading.Thread(target = self._keep_printing_stderr)
        self._stderr_printer.start()
        
        self._read_tag(protocol.OUT_TAG_INIT)
        
        info_msg = self._proc.stdout.read(protocol.init_struct.size)
        audio_length, sample_rate = protocol.from_info_msg(info_msg)

        print_err("gansynth_worker is ready")
        self._outlet(1, ["worker", "on", audio_length, sample_rate])

    def unload_1(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
            self._stderr_printer = None
        else:
            print_err("no gansynth_worker process is running")

        self._outlet(1, ["worker", "off"])
        
    def load_ganspace_components_1(self, ganspace_components_file):
        ganspace_components_file = os.path.join(
            self._canvas_dir,
            str(ganspace_components_file)
        )

        print_err("Loading GANSpace components...")

        size_msg = protocol.to_int_msg(len(ganspace_components_file))
        components_msg = ganspace_components_file.encode('utf-8')

        self._write_msg(protocol.IN_TAG_LOAD_COMPONENTS, size_msg, components_msg)
        self._read_tag(protocol.OUT_TAG_LOAD_COMPONENTS)
        count_msg = self._proc.stdout.read(protocol.count_struct.size)
        self._component_count = protocol.from_count_msg(count_msg)
        print_err("_component_count =", self._component_count)
        
        buf = pyext.Buffer(self._edits_buf_name)
        #buf.resize(component_count)
        #buf.dirty()

        print_err("GANSpace components loaded!")
        
    def next_step_1(self):
        self._read_edits()
        self._step_ix = (self._step_ix + 1) % len(self._steps) if self._steps else -1
        self._write_edits()
        self.updated()

    def prev_step_1(self):
        self._read_edits()
        self._step_ix = (self._step_ix - 1) % len(self._steps) if self._steps else -1
        self._write_edits()
        self.updated()

    def add_step_1(self):
        self._read_edits()
        self._steps.append(self._new_step())
        self._step_ix = len(self._steps) - 1
        self._write_edits()
        self.updated()
        
    def remove_step_1(self):
        self._read_edits()
        if len(self._steps) > 1:
            del self._steps[self._step_ix]

            self._step_ix = min(self._step_ix, len(self._steps)-1)
            self._write_edits()

        self.updated()

    def interp_steps_1(self, interp_steps):
        self._interp_steps = max(0, interp_steps)
        self.updated()

    def sample_spacing_1(self, sample_spacing):
        self._sample_spacing = sample_spacing
        self.updated()

    def start_trim_1(self, start_trim):
        self._start_trim = start_trim
        self.updated()

    def attack_1(self, attack):
        self._attack = attack
        self.updated()

    def sustain_1(self, sustain):
        self._sustain = sustain
        self.updated()

    def release_1(self, release):
        self._release = release
        self.updated()

    def send_state_1(self):
        state = [
            (("step", "index"), self._step_ix),
            (("step", "count"), len(self._steps)),
            (("settings", "interp_steps"), self._interp_steps),
            (("settings", "sample_spacing"), self._sample_spacing),
            (("settings", "start_trim"), self._start_trim),
            (("settings", "attack"), self._attack),
            (("settings", "sustain"), self._sustain),
            (("settings", "release"), self._release)
        ]

        for k, v in state:
            self._outlet(1, [*k, v])        
            
    def updated(self):
        self._outlet(1, "updated")
            
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
        tag_msg = self._proc.stdout.read(protocol.tag_struct.size)
        tag = protocol.from_tag_msg(tag_msg)

        if tag != expected_tag:
            raise ValueError("expected tag {}, got {}".format(expected_tag, tag))

    def _print_steps(self):
        print_err(f"_steps = {self._steps}")
        for i, step in enumerate(self._steps):
            edits = list(step["edits"])
            print_err(f"{i+1}: {edits}")
        
    def _read_edits(self):
        if not self._steps:
            return

        self._steps[self._step_ix]["edits"][:] = pyext.Buffer(self._edits_buf_name)
        # print_err("_read_edits()")
        # self._print_steps()
        
    def _write_edits(self):
        if not self._steps:
            return

        # print_err("_write_edits()")
        # self._print_steps()
        buf = pyext.Buffer(self._edits_buf_name)
        buf[:] = self._steps[self._step_ix]["edits"]
        buf.dirty()

    def _new_step(self):
        if self._steps:
            edits = self._steps[self._step_ix]["edits"].copy()
        else:
            edits = np.zeros(len(pyext.Buffer(self._edits_buf_name)), dtype=np.float32)
        step = {"edits": edits}
        return step
        
    def randomize_z_1(self, *buf_names):
        if not self._proc:
            raise Exception("can't randomize z - no gansynth_worker process is running")

        in_count = len(buf_names)

        if in_count == 0:
            raise ValueError("no buffer name(s) specified")
        
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_RAND_Z, in_count_msg)
        
        self._read_tag(protocol.OUT_TAG_Z)

        out_count_msg = self._proc.stdout.read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        assert out_count == in_count

        for buf_name in buf_names:
            z_msg = self._proc.stdout.read(protocol.z_struct.size)
            z = protocol.from_z_msg(z_msg)

            z32 = z.astype(np.float32)
        
            buf = pyext.Buffer(buf_name)
            if len(buf) != len(z32):
                buf.resize(len(z32))

            buf[:] = z32
            buf.dirty()

        self._outlet(1, "randomized")

    def save_z_1(self, z_name, path):
        save_z_buf(z_name, path)
        #np.save(z, path_fixed)
                
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

        out_count_msg = self._proc.stdout.read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)

        assert out_count == 1

        z_msg = self._proc.stdout.read(protocol.z_struct.size)
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

        gen_audio_msgs = []
        audio_buf_names = []
        for i in range(0, arg_count, 3):
            z_buf_name, audio_buf_name, pitch = args[i:i+3]

            z32_buf = pyext.Buffer(z_buf_name)
            z = np.array(z32_buf, dtype=np.float64)
            
            gen_audio_msgs.append(protocol.to_gen_audio_msg(pitch, z))
            audio_buf_names.append(audio_buf_name)
            
        in_count = len(gen_audio_msgs)
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_GEN_AUDIO, in_count_msg, *gen_audio_msgs)
                
        self._read_tag(protocol.OUT_TAG_AUDIO)

        out_count_msg = self._proc.stdout.read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        if out_count == 0:
            return

        assert out_count == in_count

        for audio_buf_name in audio_buf_names:
            audio_size_msg = self._proc.stdout.read(protocol.audio_size_struct.size)
            audio_size = protocol.from_audio_size_msg(audio_size_msg)

            audio_msg = self._proc.stdout.read(audio_size)
            audio_note = protocol.from_audio_msg(audio_msg)

            audio_buf = pyext.Buffer(audio_buf_name)
            if len(audio_buf) != len(audio_note):
                audio_buf.resize(len(audio_note))

            audio_buf[:] = audio_note
            audio_buf.dirty()
        
        self._outlet(1, "synthesized")

    # expected format: synthesize_noz buf1 pitch1 [edit1_1 edit1_2 ...] -- buf2 pitch2 [...] -- [...]
    def synthesize_noz_1(self, *args):
        if not self._proc:
            raise Exception("can't synthesize - no gansynth_worker process is running")

        # parse the input
        
        init_sound = lambda: SimpleNamespace(buf=None, pitch=None, edits=[])
        
        sounds = [init_sound()]
        i = 0
        for arg in args:
            if str(arg) == "--":
                sounds.append(init_sound())
                i = 0
            else:
                if i == 0:
                    sounds[-1].buf = arg
                elif i == 1:
                    sounds[-1].pitch = arg
                else:
                    sounds[-1].edits.append(arg)

                i += 1
                
        # validate input and build synthesize messages
        
        synth_msgs = []
        for sound in sounds:
            if None in [sound.buf, sound.pitch]:
                raise ValueError("invalid syntax, should be: synthesize_noz buf1 pitch1 [edit1_1 edit1_2 ...] [-- buf2 pitch2 [edit2_1 edit2_2 ...]] [-- ...")

            edits = []
            for edit in sound.edits:
                if isinstance(edit, pyext.Symbol):
                    # edit refers to a Pd array
                    edits_buf = pyext.Buffer(edit)
                    for val in edits_buf:
                        edits.append(val)
                else:
                    # edit is a number, probably
                    edits.append(edit)
            
            synth_msgs.append(protocol.to_synthesize_noz_msg(sound.pitch, len(edits)))
            for edit in edits:
                synth_msgs.append(protocol.to_f64_msg(edit))

        # write synthesize messages
        
        in_count = len(sounds)
        in_count_msg = protocol.to_count_msg(in_count)
        self._write_msg(protocol.IN_TAG_SYNTHESIZE_NOZ, in_count_msg, *synth_msgs)
        
        # wait for output

        self._read_tag(protocol.OUT_TAG_AUDIO)

        out_count_msg = self._read(protocol.count_struct.size)
        out_count = protocol.from_count_msg(out_count_msg)
        
        assert out_count == in_count

        if out_count == 0:
            return

        for sound in sounds:
            audio_size_msg = self._read(protocol.audio_size_struct.size)
            audio_size = protocol.from_audio_size_msg(audio_size_msg)

            audio_msg = self._read(audio_size)
            audio_note = protocol.from_audio_msg(audio_msg)

            audio_buf_name = sound.buf
            audio_buf = pyext.Buffer(audio_buf_name)
            if len(audio_buf) != len(audio_note):
                audio_buf.resize(len(audio_note))

            audio_buf[:] = audio_note
            audio_buf.dirty()
        
        self._outlet(1, "synthesized")
        
    def hallucinate_noz_1(self, audio_buf_name):
        if not self._proc:
            raise Exception("can't hallucinate - load a checkpoint first")

        if not self._steps:
            raise Exception("can't hallucinate - no steps added")

        self._read_edits()
        
        step_count = len(self._steps)
        print_err("step_count =", step_count)

        print_err("steps =", self._steps)

        edit_count = len(self._steps[0]["edits"])
        
        edit_list = []
        for step in self._steps:
            for edit in step["edits"]:
                edit_list.append(edit)

        print_err("len(edit_list) =", len(edit_list))
        
        self._write_msg(
            protocol.IN_TAG_HALLUCINATE_NOZ,
            protocol.to_hallucinate_msg(
                step_count,
                self._interp_steps,
                self._sample_spacing,
                self._start_trim,
                self._attack,
                self._sustain,
                self._release
            ),
            protocol.to_count_msg(edit_count),
            *map(protocol.to_f64_msg, edit_list)
        )
        
        self._read_tag(protocol.OUT_TAG_AUDIO)
        
        audio_size_msg = self._proc.stdout.read(protocol.audio_size_struct.size)
        audio_size = protocol.from_audio_size_msg(audio_size_msg)

        audio_msg = self._proc.stdout.read(audio_size)
        audio = protocol.from_audio_msg(audio_msg)

        audio_buf = pyext.Buffer(audio_buf_name)
        if len(audio_buf) != len(audio):
            audio_buf.resize(len(audio))

        audio_buf[:] = audio
        audio_buf.dirty()
        
        self._outlet(1, ["hallucinated", len(audio)])
