import argparse
import os

import librosa
import numpy as np
import soundfile as sf

parser = argparse.ArgumentParser()
parser.add_argument("in_dir")
parser.add_argument("out_dir")
parser.add_argument("--sample_rate", type=int, default=16000)
parser.add_argument("--len", type=int, default=64000)
parser.add_argument("--step", type=int, default=64000)
parser.add_argument("--pitch", type=int, default=32)

args = parser.parse_args()

os.makedirs(args.out_dir)

for fn in os.listdir(args.in_dir):
  name, ext = os.path.splitext(fn)

  if ext.lower() not in ".wav":
    continue

  path = os.path.join(args.in_dir, fn)
  print(path)

  audio, sr = librosa.load(path, sr = args.sample_rate, mono = True)

  dur = len(audio)
  print("  duration: {} samples".format(dur))
  parts = dur // args.step + 1
  print("  parts: {}".format(parts))
  
  i = 0
  start = 0
  while True:
    end = start + args.len

    if end > dur:
      break

    dst = os.path.join(args.out_dir, "{}_{}_{}.wav".format(name, i+1, args.pitch))
    print("  part {}/{} ({}:{}) -> {}".format(i+1, parts, start, end, dst))

    seg = audio[start:end]
    sf.write(dst, seg, args.sample_rate, subtype="PCM_16")
    
    i += 1
    start += args.step      
