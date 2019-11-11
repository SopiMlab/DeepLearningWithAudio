from __future__ import print_function

print("loading gansynth")
import sys

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

import numpy as np

import gansynth_struct as gss

script_dir = os.path.dirname(os.path.realpath(__file__))

class gansynth(pyext._class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1
        self._proc = None
        self._stderr_printer = None

    def load_1(self, ckpt_dir, batch_size=1):
        if self._proc != None:
            self.unload_1()
        
        python = sys.executable
        gen_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), "gansynth_gen.py")
        ckpt_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), str(ckpt_dir))

        print("starting gansynth_gen process, this may take a while", file=sys.stderr)

        self._proc = subprocess.Popen(
            (python, gen_script, ckpt_dir, str(batch_size)),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        self._stderr_printer = threading.Thread(target = self._keep_printing_stderr)
        self._stderr_printer.start()
        
        self._read_tag(gss.OUT_TAG_INIT)
        print("gansynth_gen is ready", file=sys.stderr)
        self._outlet(1, "loaded")

    def unload_1(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
            self._stderr_printer = None
        else:
            print("no gansynth_gen process is running", file=sys.stderr)

        self._outlet(1, "unloaded")

    def _keep_printing_stderr(self):
        while True:
            line = self._proc.stderr.readline()
            
            if not line:
                break

            sys.stderr.write("[gansynth_gen] {}".format(line))
            sys.stderr.flush()
        
    def _write_tag(self, tag):
        tag_msg = gss.to_tag_msg(tag)
        self._proc.stdin.write(tag_msg)

    def _read_tag(self, expected_tag):
        tag_msg = self._proc.stdout.read(gss.tag_struct.size)
        tag = gss.from_tag_msg(tag_msg)

        if tag != expected_tag:
            raise ValueError("expected tag {}, got {}".format(expected_tag, tag))
        
    def randomize_z_1(self, *buf_names):
        if not self._proc:
            raise Exception("can't randomize z - load a checkpoint first")

        in_count = len(buf_names)

        if in_count == 0:
            raise ValueError("no buffer name(s) specified")
        
        self._write_tag(gss.IN_TAG_RAND_Z)

        in_count_msg = gss.to_count_msg(in_count)
        self._proc.stdin.write(in_count_msg)
        
        self._read_tag(gss.OUT_TAG_Z)

        out_count_msg = self._proc.stdout.read(gss.count_struct.size)
        out_count = gss.from_count_msg(out_count_msg)

        assert out_count == in_count

        for buf_name in buf_names:
            z_msg = self._proc.stdout.read(gss.z_struct.size)
            z = gss.from_z_msg(z_msg)

            z32 = z.astype(np.float32)
        
            buf = pyext.Buffer(buf_name)
            if len(buf) != len(z32):
                buf.resize(len(z32))

            buf[:] = z32
            buf.dirty()

        self._outlet(1, "randomized")
        
    def synthesize_1(self, *args):
        if not self._proc:
            raise Exception("can't synthesize - load a checkpoint first")
        
        arg_count = len(args)
        
        if arg_count == 0 or arg_count % 3 != 0:
            raise ValueError("invalid number of arguments ({}), should be a multiple of 3: synthesize z1 audio1 pitch1 [z2 audio2 pitch2 ...]".format(arg_count))

        gen_msgs = []
        audio_buf_names = []
        for i in xrange(0, arg_count, 3):
            z_buf_name, audio_buf_name, pitch = args[i:i+3]

            z32_buf = pyext.Buffer(z_buf_name)
            z = np.array(z32_buf, dtype=np.float64)
            
            gen_msgs.append(gss.to_gen_msg(pitch, z))
            audio_buf_names.append(audio_buf_name)
            
        self._write_tag(gss.IN_TAG_GEN_AUDIO)

        in_count = len(gen_msgs)
        in_count_msg = gss.to_count_msg(in_count)
        self._proc.stdin.write(in_count_msg)

        for gen_msg in gen_msgs:
            self._proc.stdin.write(gen_msg)
        
        self._read_tag(gss.OUT_TAG_AUDIO)

        out_count_msg = self._proc.stdout.read(gss.count_struct.size)
        out_count = gss.from_count_msg(out_count_msg)

        assert out_count == in_count

        for audio_buf_name in audio_buf_names:
            audio_size_msg = self._proc.stdout.read(gss.audio_size_struct.size)
            audio_size = gss.from_audio_size_msg(audio_size_msg)

            audio_msg = self._proc.stdout.read(audio_size)
            audio_note = gss.from_audio_msg(audio_msg)

            audio_buf = pyext.Buffer(audio_buf_name)
            if len(audio_buf) != len(audio_note):
                audio_buf.resize(len(audio_note))

            audio_buf[:] = audio_note
            audio_buf.dirty()
        
        self._outlet(1, "synthesized")
