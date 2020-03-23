# timbre transfer
# based on the timbre_transfer.ipynb example from ddsp
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import warnings
warnings.filterwarnings("ignore")

import argparse
import copy
import os
import time

import crepe
import ddsp
import ddsp.training
import gin
import librosa
import numpy as np
import scipy
import tensorflow.compat.v2 as tf

parser = argparse.ArgumentParser()

parser.add_argument("--ckpt_dir", required=True)
parser.add_argument("--in_file", required=True)
parser.add_argument("--out_file", required=True)
parser.add_argument("--sample_rate", type=int, default=16000)
parser.add_argument("--f0_octave_shift", type=int, default=0)
parser.add_argument("--f0_confidence_threshold", type=float, default=0.0)
parser.add_argument("--loudness_db_shift", type=float, default=0.0)
parser.add_argument("--auto_adjust_preset")

args = parser.parse_args()

# load audio
audio_sample_rate, audio = scipy.io.wavfile.read(args.in_file)
dtype = audio.dtype
audio = audio.astype(np.float32)
if np.issubdtype(dtype, np.integer):
    audio = audio / np.iinfo(dtype).max
audio = audio[np.newaxis, :]

print('\nExtracting audio features...')

# Setup the session.
ddsp.spectral_ops.reset_crepe()

# Compute features.
start_time = time.time()
audio_features = ddsp.training.eval_util.compute_audio_features(audio)
audio_features['loudness_db'] = audio_features['loudness_db'].astype(np.float32)
audio_features_mod = None
print('Audio features took %.1f seconds' % (time.time() - start_time))

model_dir = args.ckpt_dir
gin_file = os.path.join(model_dir, 'operative_config-0.gin')

# Parse gin config,
with gin.unlock_config():
    gin.parse_config_file(gin_file, skip_unknown=True)

# Assumes only one checkpoint in the folder, 'ckpt-[iter]`.
ckpt_files = [f for f in tf.io.gfile.listdir(model_dir) if 'ckpt' in f]
ckpt_name = ckpt_files[0].split('.')[0]
ckpt = os.path.join(model_dir, ckpt_name)

# Ensure dimensions and sampling rates are equal
time_steps_train = gin.query_parameter('DefaultPreprocessor.time_steps')
n_samples_train = gin.query_parameter('Additive.n_samples')
hop_size = int(n_samples_train / time_steps_train)

time_steps = int(audio.shape[1] / hop_size)
n_samples = time_steps * hop_size

gin_params = [
    'Additive.n_samples = {}'.format(n_samples),
    'FilteredNoise.n_samples = {}'.format(n_samples),
    'DefaultPreprocessor.time_steps = {}'.format(time_steps),
]

with gin.unlock_config():
  gin.parse_config(gin_params)


# Trim all input vectors to correct lengths 
for key in ['f0_hz', 'f0_confidence', 'loudness_db']:
    audio_features[key] = audio_features[key][:time_steps]
audio_features['audio'] = audio_features['audio'][:, :n_samples]


# Set up the model just to predict audio given new conditioning
model = ddsp.training.models.Autoencoder()
model.restore(ckpt)

# Build model by running a batch through it.
start_time = time.time()
_ = model(audio_features, training=False)
print('Restoring model took %.1f seconds' % (time.time() - start_time))

#@markdown You can also make additional manual adjustments:
#@markdown * Shift the fundmental frequency to a more natural register.
#@markdown * Silence audio below a threshold on f0_confidence.
#@markdown * Adjsut the overall loudness level.
f0_octave_shift = args.f0_octave_shift
f0_confidence_threshold = args.f0_confidence_threshold
loudness_db_shift = args.loudness_db_shift

#@markdown You might get more realistic sounds by shifting a few dB, or try going extreme and see what weird sounds you can make...

audio_features_mod = {k: v.copy() for k, v in audio_features.items()}

## Helper functions.
def shift_ld(audio_features, ld_shift=0.0):
    """Shift loudness by a number of octaves."""
    audio_features['loudness_db'] += ld_shift
    return audio_features


def shift_f0(audio_features, f0_octave_shift=0.0):
    """Shift f0 by a number of octaves."""
    audio_features['f0_hz'] *= 2.0 ** (f0_octave_shift)
    audio_features['f0_hz'] = np.clip(
        audio_features['f0_hz'], 
        0.0, 
        librosa.midi_to_hz(110.0)
    )
    return audio_features

def mask_by_confidence(audio_features, confidence_level=0.1):
    """For the violin model, the masking causes fast dips in loudness. 
    This quick transient is interpreted by the model as the "plunk" sound.
    """
    mask_idx = audio_features['f0_confidence'] < confidence_level
    audio_features['f0_hz'][mask_idx] = 0.0
    # audio_features['loudness_db'][mask_idx] = -ddsp.spectral_ops.LD_RANGE
    return audio_features

def smooth_loudness(audio_features, filter_size=3):
    """Smooth loudness with a box filter."""
    smoothing_filter = np.ones([filter_size]) / float(filter_size)
    audio_features['loudness_db'] = np.convolve(
        audio_features['loudness_db'],
        smoothing_filter, 
        mode='same'
    )
    return audio_features

MODEL = args.auto_adjust_preset.lower() if args.auto_adjust_preset else None

if MODEL in ['Violin', 'Flute', 'Flute2', 'Trumpet', 'Saxophone', 'Tenor_Saxophone']:
    # Adjust the peak loudness.
    l = audio_features['loudness_db']
    model_ld_avg_max = {
        'Violin': -34.0,
        'Flute': -45.0,
        'Flute2': -44.0,
        'Trumpet': -52.3,
        'Saxophone': -44.0,
        'Tenor_Saxophone': -31.2
    }[MODEL]
    ld_max = np.max(audio_features['loudness_db'])
    ld_diff_max = model_ld_avg_max - ld_max
    audio_features_mod = shift_ld(audio_features_mod, ld_diff_max)
    
    # Further adjust the average loudness above a threshold.
    l = audio_features_mod['loudness_db']
    model_ld_mean = {
        'Violin': -44.0,
        'Flute': -51.0,
        'Flute2': -53.0,
        'Trumpet': -69.2,
        'Saxophone': -57.7,
        'Tenor_Saxophone': -50.8
    }[MODEL]
    ld_thresh = -70.0
    ld_mean = np.mean(l[l > ld_thresh])
    ld_diff_mean = model_ld_mean - ld_mean
    audio_features_mod = shift_ld(audio_features_mod, ld_diff_mean)
    
    # Shift the pitch register.
    model_p_mean = {
        'Violin': 73.0,
        'Flute': 81.0,
        'Flute2': 74.0,
        'Trumpet': 65.8,
        'Saxophone': 66.1,
        'Tenor_Saxophone': 57.8
    }[MODEL]
    p = librosa.hz_to_midi(audio_features['f0_hz'])
    p[p == -np.inf] = 0.0
    p_mean = p[l > ld_thresh].mean()
    p_diff = model_p_mean - p_mean
    p_diff_octave = p_diff / 12.0
    round_fn = np.floor if p_diff_octave > 1.5 else np.ceil
    p_diff_octave = round_fn(p_diff_octave)
    audio_features_mod = shift_f0(audio_features_mod, p_diff_octave)

audio_features_mod = shift_ld(audio_features_mod, loudness_db_shift)
audio_features_mod = shift_f0(audio_features_mod, f0_octave_shift)
audio_features_mod = mask_by_confidence(audio_features_mod, f0_confidence_threshold)

af = audio_features if audio_features_mod is None else audio_features_mod

# Run a batch of predictions.
start_time = time.time()
audio_gen = model(af, training=False)
print('Prediction took %.1f seconds' % (time.time() - start_time))

scipy.io.wavfile.write(args.out_file, args.sample_rate, audio_gen.numpy().T)
