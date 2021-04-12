# timbre transfer
# based on the timbre_transfer.ipynb example from ddsp
import warnings
warnings.filterwarnings("ignore")

import argparse
import os
import time
import sys
import pickle
import traceback

import crepe
import ddsp
import ddsp.training
from ddsp.colab import colab_utils
from ddsp.colab.colab_utils import (
    auto_tune, detect_notes, fit_quantile_transform, 
    get_tuning_factor
)
import gin
import librosa
import numpy as np
import scipy
import tensorflow.compat.v2 as tf

import sopilib.ddsp_protocol as protocol
from sopilib.utils import print_err, read_msg

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



def timbre_transfer(
    ckpt_dir,
    audio,
    in_sample_rate,
    out_sample_rate,
    f0_octave_shift,
    f0_confidence_threshold,
    loudness_db_shift,
    adjust,
    quiet,
    autotune,
    log=print
):
    log("converting audio...")
    start_time = time.time()
    audio = librosa.to_mono(audio)
    audio = librosa.resample(audio, in_sample_rate, out_sample_rate)
    audio = audio[np.newaxis, :]
    duration = time.time() - start_time
    log("done - {:.1f} s".format(duration))
    
    # Setup the session.
    ddsp.spectral_ops.reset_crepe()

    # Compute features.
    log("computing audio features...")
    start_time = time.time()
    audio_features = ddsp.training.metrics.compute_audio_features(audio)
    audio_features['loudness_db'] = audio_features['loudness_db'].astype(np.float32)
    audio_features_mod = None
    duration = time.time() - start_time
    log("done - {:.1f} s".format(duration))

    model_dir = ckpt_dir
    gin_file = os.path.join(model_dir, 'operative_config-0.gin')

    dataset_stats = None
    dataset_stats_file = os.path.join(model_dir, 'dataset_statistics.pkl')
    log(f'Loading dataset statistics from {dataset_stats_file}')
    try:
        if tf.io.gfile.exists(dataset_stats_file):
            with tf.io.gfile.GFile(dataset_stats_file, 'rb') as f:
                dataset_stats = pickle.load(f)
    except Exception as err:
        traceback.print_exc(file=sys.stderr)
        log('Loading dataset statistics from pickle failed!')
    
    # Parse gin config,
    with gin.unlock_config():
        gin.parse_config_file(gin_file, skip_unknown=True)

    # Assumes only one checkpoint in the folder, 'ckpt-[iter]`.
    ckpt_files = [f for f in tf.io.gfile.listdir(model_dir) if 'ckpt' in f]
    ckpt_name = ckpt_files[0].split('.')[0]
    ckpt = os.path.join(model_dir, ckpt_name)

    # Ensure dimensions and sampling rates are equal
    time_steps_train = gin.query_parameter('F0LoudnessPreprocessor.time_steps')
    n_samples_train = gin.query_parameter('Harmonic.n_samples')
    hop_size = int(n_samples_train / time_steps_train)

    time_steps = int(audio.shape[1] / hop_size)
    n_samples = time_steps * hop_size

    gin_params = [
        'Harmonic.n_samples = {}'.format(n_samples),
        'FilteredNoise.n_samples = {}'.format(n_samples),
        'F0LoudnessPreprocessor.time_steps = {}'.format(time_steps),
        'oscillator_bank.use_angular_cumsum = True',  # Avoids cumsum accumulation errors.
    ]

    with gin.unlock_config():
        gin.parse_config(gin_params)

    # Trim all input vectors to correct lengths 
    for key in ['f0_hz', 'f0_confidence', 'loudness_db']:
        audio_features[key] = audio_features[key][:time_steps]
    audio_features['audio'] = audio_features['audio'][:, :n_samples]

    # Set up the model just to predict audio given new conditioning
    log("restoring model...")
    start_time = time.time()
    model = ddsp.training.models.Autoencoder()
    model.restore(ckpt)

    # Build model by running a batch through it.
    _ = model(audio_features, training=False)
    duration = time.time() - start_time
    log("done - {:.1f} s".format(duration))

    # Modify conditioning
    
    audio_features_mod = {k: v.copy() for k, v in audio_features.items()}
    
    mask_on = None
    if adjust and dataset_stats != None:
          mask_on, note_on_value = detect_notes(
              audio_features['loudness_db'],
              audio_features['f0_confidence'],
              f0_confidence_threshold
          )

          if np.any(mask_on):
              # Shift the pitch register.
              target_mean_pitch = dataset_stats['mean_pitch']
              pitch = ddsp.core.hz_to_midi(audio_features['f0_hz'])
              mean_pitch = np.mean(pitch[mask_on])
              p_diff = target_mean_pitch - mean_pitch
              p_diff_octave = p_diff / 12.0
              round_fn = np.floor if p_diff_octave > 1.5 else np.ceil
              p_diff_octave = round_fn(p_diff_octave)
              audio_features_mod = shift_f0(audio_features_mod, p_diff_octave)

              # Quantile shift the note_on parts.
              _, loudness_norm = colab_utils.fit_quantile_transform(
                  audio_features['loudness_db'],
                  mask_on,
                  inv_quantile=dataset_stats['quantile_transform']
              )

              # Turn down the note_off parts.
              mask_off = np.logical_not(mask_on)
              loudness_norm[mask_off] -=  quiet * (1.0 - note_on_value[mask_off][:, np.newaxis])
              loudness_norm = np.reshape(loudness_norm, audio_features['loudness_db'].shape)
    
              audio_features_mod['loudness_db'] = loudness_norm 
              
              # Auto-tune.
              if autotune:
                  f0_midi = np.array(ddsp.core.hz_to_midi(audio_features_mod['f0_hz']))
                  tuning_factor = get_tuning_factor(f0_midi, audio_features_mod['f0_confidence'], mask_on)
                  f0_midi_at = auto_tune(f0_midi, tuning_factor, mask_on, amount=autotune)
                  audio_features_mod['f0_hz'] = ddsp.core.midi_to_hz(f0_midi_at)
    #       else:
    #           log('\nSkipping auto-adjust (no notes detected or ADJUST box empty).')
    # else:
    #     log('\nSkipping auto-adujst (box not checked or no dataset statistics found).')

    audio_features_mod = shift_ld(audio_features_mod, loudness_db_shift)
    audio_features_mod = shift_f0(audio_features_mod, f0_octave_shift)
    audio_features_mod = mask_by_confidence(audio_features_mod, f0_confidence_threshold)

    # Resynthesize audio
    
    af = audio_features if audio_features_mod is None else audio_features_mod

    # Run a batch of predictions.
    log("predicting...")
    start_time = time.time()
    outputs = model(af, training=False)
    audio_gen = model.get_audio_from_outputs(outputs)
    duration = time.time() - start_time
    log("done - {:.1f} s".format(duration))
    
    return audio_gen

def handle_timbre_transfer(stdin, stdout):
    transfer_msg = read_msg(stdin, protocol.timbre_transfer_struct.size)
    h = protocol.from_timbre_transfer_msg(transfer_msg)
    print_err(repr(h))
    in_sample_rate, out_sample_rate, f0_octave_shift, f0_confidence_threshold, loudness_db_shift, adjust, quiet, autotune, ckpt_dir_len, in_audio_len = h
    
    print_err("ckpt_dir_len =", ckpt_dir_len)
    print_err("in_audio_len =", in_audio_len)
    ckpt_dir_msg = stdin.read(ckpt_dir_len)
    ckpt_dir = protocol.from_str_msg(ckpt_dir_msg)
    print_err("ckpt_dir =", ckpt_dir)
    
    in_audio_msg = stdin.read(in_audio_len)
    print_err("len(in_audio_msg) =", len(in_audio_msg))
    in_audio = protocol.from_audio_msg(in_audio_msg)
    print_err("in_audio.size =", in_audio.size)
    
    out_audio = timbre_transfer(
        ckpt_dir = ckpt_dir,
        audio = in_audio,
        in_sample_rate = in_sample_rate,
        out_sample_rate = out_sample_rate,
        f0_octave_shift = f0_octave_shift,
        f0_confidence_threshold = f0_confidence_threshold,
        loudness_db_shift = loudness_db_shift,
        adjust = adjust,
        quiet = quiet,
        autotune = autotune,
        log = print_err
    )
    out_audio = out_audio.numpy().ravel()

    out_audio_len = out_audio.size * out_audio.itemsize
    
    print_err("out_audio.shape =", out_audio.shape)
    print_err("out_audio_len =", out_audio_len)
    
    stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_TIMBRE_TRANSFERRED))
    print_err("wrote tag_timbre_transferred")
    
    stdout.write(protocol.to_timbre_transferred_msg(out_audio_len))
    print_err("wrote size")
    bytez = protocol.to_audio_msg(out_audio)
    print_err("len(bytez) =", len(bytez))
    stdout.write(bytez)
    print_err("wrote out_audio")
    stdout.flush()

handlers = {
    protocol.IN_TAG_TIMBRE_TRANSFER: handle_timbre_transfer
}

if __name__ == "__main__":    
    parser = argparse.ArgumentParser()

    parser.add_argument("--ckpt_dir", required=True)
    parser.add_argument("--in_file", required=True)
    parser.add_argument("--out_file", required=True)
    parser.add_argument("--sample_rate", type=int, default=16000)
    parser.add_argument("--f0_octave_shift", type=int, default=0)
    parser.add_argument("--f0_confidence_threshold", type=float, default=0.0)
    parser.add_argument("--loudness_db_shift", type=float, default=0.0)
    parser.add_argument("--adjust", dest="adjust", action="store_true")
    parser.add_argument("--no-adjust", dest="adjust", action="store_false")
    parser.set_defaults(adjust=True)
    parser.add_argument("--quiet", type=float, default=20.0)
    parser.add_argument("--autotune", type=float, default=0.0)
    
    args = parser.parse_args()

    audio, in_sample_rate = librosa.load(args.in_file, sr=None)

    out_audio = timbre_transfer(
        ckpt_dir = args.ckpt_dir,
        audio = audio,
        in_sample_rate = in_sample_rate,
        out_sample_rate = args.sample_rate,
        f0_octave_shift = args.f0_octave_shift,
        f0_confidence_threshold = args.f0_confidence_threshold,
        loudness_db_shift = args.loudness_db_shift,
        adjust = args.adjust,
        quiet = args.quiet,
        autotune = args.autotune,
        log = print_err
    )

    print_err("saving generated audio to {}".format(args.out_file))
    scipy.io.wavfile.write(args.out_file, args.sample_rate, out_audio.numpy().T)
