import argparse
import os
import re
import sys

parser = argparse.ArgumentParser()

parser.add_argument(
  "in_dir"
)
parser.add_argument(
  "out_dir"
)
parser.add_argument(
  "--length",
  type=int,
  default=64000
)
parser.add_argument(
  "--sample_rate",
  type=int,
  default=16000
)
parser.add_argument(
  "--pitch",
  type=int,
  default=32
)
args = parser.parse_args()
  
import librosa
import numpy as np
import soundfile as sf

def print_err(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)
  sys.stderr.flush()

def splitext_all(name):
  m = re.match("^(.*?)((?:\.[^.]*)*)$", name)
  return (m.group(1), m.group(2))

try:
  os.makedirs(args.out_dir)
except FileExistsError:
  # ok
  pass

counts = {}

def traverse(in_dir_path, prefix=()):
  for in_item_name in os.listdir(in_dir_path):
    in_item_path = os.path.join(in_dir_path, in_item_name)

    if os.path.isdir(in_item_path):
      traverse(in_item_path, prefix + (in_item_name,))
      continue

    ext = os.path.splitext(in_item_name)[1].lower()
    if ext not in [".wav", ".aif", ".aiff", ".mp3"]:
      continue

    print_err("/".join(prefix+(in_item_name,)))

    prefix_str = "-".join(prefix) if prefix else ""
    out_identifier = re.sub(r"[^a-z0-9]+", "-", prefix_str.lower())
    counts[out_identifier] = counts.setdefault(out_identifier, 0) + 1
    
    out_file_name = "{}-{}_{}.wav".format(out_identifier, counts[out_identifier], args.pitch)
    out_file_path = os.path.join(args.out_dir, out_file_name)
    
    audio, sr = librosa.load(in_item_path, sr=args.sample_rate, mono=True)
    
    audio_len = len(audio)
    
    print_err("  length: {} samples".format(audio_len))
    if audio_len > args.length:
      print_err("  will be truncated")
      
    out_audio = np.zeros(args.length, dtype=audio.dtype)
    
    copy_stop_i = min(args.length, audio_len)
    out_audio[:copy_stop_i] = librosa.util.normalize(audio[:copy_stop_i])
    
    # librosa.output.write_wav(out_file_path, out_audio, sr=args.sample_rate, norm=True)
    sf.write(out_file_path, out_audio, args.sample_rate, subtype="PCM_16")
    print_err("  -> {}".format(out_file_name))
    
traverse(args.in_dir)
