from __future__ import absolute_import
from __future__ import print_function

import argparse
import json
import os
import re
import sys
import wave

parser = argparse.ArgumentParser()

parser.add_argument("--in_dir", required=True)
parser.add_argument("--out_dir")

args = parser.parse_args()

required_sample_rate = 16000
required_audio_len = 64000
required_channels = 1

def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

in_dir = args.in_dir
if args.out_dir != None:
    out_dir = args.out_dir
else:
    in_dir_stripped = in_dir.rstrip("/")
    out_dir_name = os.path.basename(in_dir_stripped) + "-train"
    out_dir = os.path.join(os.path.dirname(in_dir_stripped), out_dir_name)
out_tfrecord_path = os.path.join(out_dir, "data.tfrecord")
out_meta_path = os.path.join(out_dir, "meta.json")

def require_nonexistent(path):
    if os.path.exists(path):
        log("{} already exists!".format(path))
        sys.exit(1)

require_nonexistent(out_tfrecord_path)
require_nonexistent(out_meta_path)

# find wav files

instruments = {}

log("scanning {} for wav files matching \"[name]_[pitch].wav\"...".format(in_dir))
for fn in os.listdir(in_dir):
    name, ext = os.path.splitext(fn)
    if not ext.lower().endswith(".wav"):
        continue

    m = re.match(r"^(.+)_(\d+)$", name)
    if not m:
        continue

    instrument = m.group(1)
    pitch = int(m.group(2))
    
    if instrument not in instruments:
        instruments[instrument] = {
            "source": 0,
            "samples": [],
            # GANSynth doesn't actually use qualities or family, so just put in
            # some mock values
            "qualities": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "family": 0,
        }

    instruments[instrument]["samples"].append({
        "pitch": pitch,
        "file": os.path.join(in_dir, fn)
    })

if len(instruments) == 0:
    log("no matching wav files found!")
    sys.exit(1)
    
log()

# validate wav files

log("validating wav files (sample rate: {}, channels: {}, length: {}, format: int16)...".format(
    required_sample_rate,
    required_channels,
    required_audio_len
))

all_valid = True

for name in sorted(instruments.keys()):
    inst = instruments[name]
    for sample in inst["samples"]:
        with wave.open(sample["file"], "rb") as wav:
            sample_rate = wav.getframerate()
            audio_len = wav.getnframes()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()

            errors = []
            
            if sample_rate != required_sample_rate:
                errors.append("invalid sample rate: {}".format(sample_rate))
            if channels != required_channels:
                errors.append("invalid channels: {}".format(channels))
            if audio_len != required_audio_len:
                errors.append("invalid length: {}".format(audio_len))
            if sample_width != 2:
                errors.append("invalid format: {} bit".format(sample_width * 8))

            if errors:
                log(os.path.basename(sample["file"]))
                for error in errors:
                    log("  {}".format(error))
                    all_valid = False

if not all_valid:
    sys.exit(1)

log()
    
# print stats

for name in sorted(instruments.keys()):
    inst = instruments[name]
    log(name)
    log("  pitches: {}".format(sorted((s["pitch"] for s in inst["samples"]))))

log()
    
# write metadata

try:
    os.makedirs(out_dir)
except FileExistsError:
    pass

log("writing metadata to {}...".format(out_meta_path))

meta = {}

for name, inst in instruments.items():
    for sample in inst["samples"]:
        full_name = "{}_{}".format(name, sample["pitch"])
        meta[full_name] = {
            "instrument_str": name,
            "pitch": sample["pitch"],
            "instrument_source": inst["source"],
            "instrument_family": inst["family"],
            "qualities": inst["qualities"]
        }

with open(out_meta_path, "w") as meta_fp:
    json.dump(meta, meta_fp, indent=4)
    
# write TFRecords

log("writing TFRecords to {}...".format(out_tfrecord_path))

import numpy as np
import scipy.io.wavfile
import tensorflow as tf

with tf.io.TFRecordWriter(out_tfrecord_path) as record_writer:
    for name, inst in instruments.items():
        for sample in inst["samples"]:
            sample_rate, audio = scipy.io.wavfile.read(sample["file"])

            float_normalizer = float(np.iinfo(np.int16).max)
            audio = audio / float_normalizer

            example = tf.train.Example(features = tf.train.Features(feature = {
                "pitch": tf.train.Feature(
                    int64_list = tf.train.Int64List(value = [sample["pitch"]])
                ),
                "audio": tf.train.Feature(
                    float_list = tf.train.FloatList(value = audio.tolist())
                ),
                "qualities": tf.train.Feature(
                    int64_list = tf.train.Int64List(value = inst["qualities"])
                ),
                "instrument_source": tf.train.Feature(
                    int64_list = tf.train.Int64List(value = [inst["source"]])
                ),
                "instrument_family": tf.train.Feature(
                    int64_list = tf.train.Int64List(value = [inst["family"]])
                )
            }))

            record_writer.write(example.SerializeToString())
