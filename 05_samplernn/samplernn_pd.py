from __future__ import print_function

import sys

try:
    import pyext
except:
    print("ERROR: This script must be loaded by the PD/Max pyext external")

import argparse
import os
import random
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np

import sopilib.samplernn_protocol as protocol
from sopilib.utils import print_err

script_dir = os.path.dirname(os.path.realpath(__file__))

class samplernn(pyext._class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1
        self._proc = None
        self._stderr_printer = None

        self._load_parser = argparse.ArgumentParser()
        self._load_parser.add_argument("--python", default=None)
        self._load_parser.add_argument("worker_args", nargs="*")
        
        self._generate_parser = argparse.ArgumentParser()
        self._generate_parser.add_argument("--seed_sr", type=int, default=16000)
        self._generate_parser.add_argument("--out_sr", type=int, default=16000)
        self._generate_parser.add_argument("--dur", type=float, default=10.0)
        self._generate_parser.add_argument("--seed", default=None)
        self._generate_parser.add_argument("--temp", type=float, action="append")
        self._generate_parser.add_argument("--out", action="append", required=True)
        
    def load_1(self, *raw_args):
        if self._proc != None:
            self.unload_1()

        args = self._load_parser.parse_args(map(str, raw_args))

        python = args.python
        if not python:
            python = sys.executable
            
        worker_script = os.path.join(script_dir, "samplernn_worker.py")
        
        print_err("starting samplernn_worker process, this may take a while")
        worker_command = (str(python), worker_script, *args.worker_args)
        print_err("worker_command =", worker_command)
        
        self._proc = subprocess.Popen(
            worker_command,
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            cwd = self._canvas_dir
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
            print_err("no samplernn_worker process is running")

        self._outlet(1, ["worker", "off"])
        
    def generate_1(self, *raw_args):
        if not self._proc:
            raise Exception("no samplernn_worker process is running")

        args = self._generate_parser.parse_args(map(str, raw_args))
        print_err("args =", args)

        outs = args.out if args.out != None else []
        temps = args.temp if args.temp != None else []
        
        num_outs = len(outs)

        if num_outs < 1:
            print_err("no outputs specified")

        while len(temps) < num_outs:
            temps.append(temps[-1])

        if args.seed != None:
            seed_buf = pyext.Buffer(args.seed)
            seed_audio = np.array(seed_buf, dtype=np.float32)
        else:
            seed_audio = np.array([], dtype=np.float32)

        print_err("seed_audio size*itemsize =", seed_audio.size * seed_audio.itemsize)
            
        seed_len = seed_audio.size * seed_audio.itemsize
        
        out_len = round(args.dur * args.out_sr)
        
        generate_msg = protocol.to_generate_msg(args.seed_sr, args.out_sr, num_outs, out_len, seed_len)
        temp_msgs = map(protocol.to_f32_msg, temps)
        seed_audio_msg = protocol.to_audio_msg(seed_audio)
        
        self._write_msg(protocol.IN_TAG_GENERATE, generate_msg, *temp_msgs, seed_audio_msg)

        print_err("wrote")
        
        self._read_tag(protocol.OUT_TAG_GENERATED)

        generated_msg = self._proc.stdout.read(protocol.generated_struct.size)

        g_out_sr, g_num_outs, g_out_len = protocol.from_generated_msg(generated_msg)

        print_err("g_out_sr =", g_out_sr)
        print_err("g_num_outs =", g_num_outs)
        print_err("g_out_len =", g_out_len)
        
        out_audios = []
        for i in range(g_num_outs):
            out_audio_msg = self._proc.stdout.read(g_out_len * protocol.f32_struct.size)
            out_audios.append(protocol.from_audio_msg(out_audio_msg))
        
        print_err("len(out_audios) =", len(out_audios))

        assert len(outs) == len(out_audios)

        for buf_name, audio in zip(outs, out_audios):
            buf = pyext.Buffer(buf_name)
            if len(buf) != len(audio):
                buf.resize(len(audio))

            buf[:] = audio
            buf.dirty()

        print_err("done")
        
    def _keep_printing_stderr(self):
        while True:
            line = self._proc.stderr.readline()
            
            if not line:
                break

            sys.stderr.write("[samplernn_worker] ")
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
        if not tag_msg:
            raise EOFError("stdout")
        tag = protocol.from_tag_msg(tag_msg)

        if tag != expected_tag:
            raise ValueError("expected tag {}, got {}".format(expected_tag, tag))
        
