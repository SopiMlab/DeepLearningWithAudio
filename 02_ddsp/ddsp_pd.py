from __future__ import print_function

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

import sopilib.ddsp_protocol as protocol
from sopilib.utils import print_err

script_dir = os.path.dirname(os.path.realpath(__file__))

def normalize(buf, target=0.9, inplace=False):
    maximum = max(buf.min(), buf.max(), key=abs)
    if maximum == 0.0:
        return buf
    factor = target/maximum
    if inplace:
        buf *= factor
        return buf
    else:
        return buf * factor

class timbre_transfer(pyext._class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1
        self._proc = None
        self._stderr_printer = None

    def load_1(self, python=None):
        if self._proc != None:
            self.unload_1()

        if not python:
            python = sys.executable
            
        worker_script = os.path.join(script_dir, "ddsp_worker.py")

        print_err("starting ddsp_worker process, this may take a while")

        self._proc = subprocess.Popen(
            (str(python), worker_script),
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )
        self._stderr_printer = threading.Thread(target = self._keep_printing_stderr)
        self._stderr_printer.start()
        
        self._read_tag(protocol.OUT_TAG_INIT)
        
        self._outlet(1, ["worker", "on"])
        
    def unload_1(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
            self._stderr_printer = None
        else:
            print_err("no ddsp_worker process is running")

        self._outlet(1, ["worker", "off"])
        
    def run_1(self, ckpt_dir, in_arr, out_arr,
        f0_octave_shift = 0,
        f0_confidence_threshold = 0.0,
        loudness_db_shift = 0.0,
        in_sample_rate = 44100,
        out_sample_rate = 16000,
        adjust = True,
        quiet = 20.0,
        autotune = 0.0
    ):
        if not self._proc:
            raise Exception("no ddsp_worker process is running")

        # get buffers
        
        in_buf = pyext.Buffer(in_arr)
        out_buf = pyext.Buffer(out_arr)

        in_audio = np.array(in_buf, dtype=np.float32)

        print_err("in_audio.size =", in_audio.size)
        print_err("in_audio.itemsize =", in_audio.itemsize)
        
        # make timbre transfer message
        
        ckpt_msg = protocol.to_str_msg(os.path.join(script_dir, str(ckpt_dir)))
        print_err("len(ckpt_msg) = ", len(ckpt_msg))
        transfer_msg = protocol.to_timbre_transfer_msg(
            in_sample_rate,
            out_sample_rate,
            f0_octave_shift,
            f0_confidence_threshold,
            loudness_db_shift,
            adjust,
            quiet,
            autotune,
            len(ckpt_msg),
            in_audio.size * in_audio.itemsize
        )
        print_err("len(transfer_msg) = ", len(transfer_msg))
        in_audio_msg = protocol.to_audio_msg(in_audio)
        print_err("len(in_audio_msg) = ", len(in_audio_msg))

        # write timbre transfer message
        
        self._write_msg(protocol.IN_TAG_TIMBRE_TRANSFER, transfer_msg, ckpt_msg, in_audio_msg)

        print_err("wrote")
        
        # read timbre transferred message
        
        self._read_tag(protocol.OUT_TAG_TIMBRE_TRANSFERRED)

        print_err("read")
        
        transferred_msg = self._proc.stdout.read(protocol.timbre_transferred_struct.size)
        print_err("len(transferred_msg) =", len(transferred_msg))
        out_audio_len = protocol.from_timbre_transferred_msg(transferred_msg)
        print_err("out_audio_len =", out_audio_len)
        out_audio_msg = self._proc.stdout.read(out_audio_len)
        print_err("len(out_audio_msg)", len(out_audio_msg))
        out_audio = protocol.from_audio_msg(out_audio_msg)

        # resize output buffer if needed
        
        if len(out_audio) != len(out_buf):
            print_err("resizing")
            out_buf.resize(len(out_audio))
            print_err("resized")
        else:
            print_err("no resize")

        # write output

        out_buf[:] = normalize(out_audio)
        print_err("wrote out_audio")
        out_buf.dirty()

        self._outlet(1, ["transferred", len(out_audio)])

    def normalize_1(self, buf_name, target=0.9):
        buf = pyext.Buffer(buf_name)
        buf[:] = normalize(np.array(buf), target)
        buf.dirty()
        self._outlet(1, "normalized")
        
    def _keep_printing_stderr(self):
        while True:
            line = self._proc.stderr.readline()
            
            if not line:
                break

            sys.stderr.write("[ddsp_worker] ")
            sys.stderr.write(line.decode("utf-8"))
            sys.stderr.flush()
        
    def _write_msg(self, tag, *msgs):
        tag_msg = protocol.to_tag_msg(tag)
        self._proc.stdin.write(tag_msg)
        for msg in msgs:
            self._proc.stdin.write(msg)
        self._proc.stdin.flush()
        
    def _read_tag(self, expected_tag):
        tag_msg = self._proc.stdout.read(protocol.tag_struct.size)
        tag = protocol.from_tag_msg(tag_msg)

        if tag != expected_tag:
            raise ValueError("expected tag {}, got {}".format(expected_tag, tag))
        
