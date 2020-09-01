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
parser.add_argument("--sample_rate", type=int, default=16000)
parser.add_argument("--length", type=int, default=64000)
parser.add_argument("--skip_validate", default=False, action="store_const", const=True)

args = parser.parse_args()

required_sample_rate = args.sample_rate
required_audio_len = args.length
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

# load data from examples.json

examples_path = os.path.join(in_dir, "examples.json")
log("loading {}...".format(examples_path))
with open(examples_path, "r") as examples_fp:
    examples_json = json.load(examples_fp)
examples = sorted(examples_json.values(), key=lambda e: e["note_str"])
log()

# validate wav files

audio_dir = os.path.join(in_dir, "audio")
if not args.skip_validate:
    log("validating wav files (sample rate: {}, channels: {}, length: {}, format: int16)...".format(
        required_sample_rate,
        required_channels,
        required_audio_len
    ))

    all_valid = True
    for example in examples:
        wav_path = os.path.join(audio_dir, "{}.wav".format(example["note_str"]))
        wav = wave.open(wav_path, "rb")
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
        wav.close()

    if not all_valid:
        sys.exit(1)

    log()

# write metadata

try:
    os.makedirs(out_dir)
except Exception:
    pass

log("writing metadata to {}...".format(out_meta_path))

meta = {}

for example in examples:
    full_name = example["note_str"]
    meta[full_name] = {
        "instrument_str": example["instrument_str"],
        "pitch": example["pitch"],
        "instrument_source": example["instrument_source"],
        "instrument_family": example["instrument_family"],
        "qualities": example["qualities"]
    }

with open(out_meta_path, "w") as meta_fp:
    json.dump(meta, meta_fp, indent=4)
    
# write TFRecords

log("writing TFRecords to {}...".format(out_tfrecord_path))

import numpy as np
import scipy.io.wavfile
import tensorflow as tf

with tf.io.TFRecordWriter(out_tfrecord_path) as record_writer:
    for example in examples:
        wav_path = os.path.join(audio_dir, "{}.wav".format(example["note_str"]))
        sample_rate, audio = scipy.io.wavfile.read(wav_path)

        float_normalizer = float(np.iinfo(np.int16).max)
        audio = audio / float_normalizer

        example = tf.train.Example(features = tf.train.Features(feature = {
            "pitch": tf.train.Feature(
                int64_list = tf.train.Int64List(value = [example["pitch"]])
            ),
            "audio": tf.train.Feature(
                float_list = tf.train.FloatList(value = audio.tolist())
            ),
            "qualities": tf.train.Feature(
                int64_list = tf.train.Int64List(value = example["qualities"])
            ),
            "instrument_source": tf.train.Feature(
                int64_list = tf.train.Int64List(value = [example["instrument_source"]])
            ),
            "instrument_family": tf.train.Feature(
                int64_list = tf.train.Int64List(value = [example["instrument_family"]])
            )
        }))
        
        record_writer.write(example.SerializeToString())
