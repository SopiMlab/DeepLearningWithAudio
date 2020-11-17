import math
import os
import pickle
import time

import absl.flags
from magenta.models.gansynth.lib import flags as lib_flags
from magenta.models.gansynth.lib import generate_util as gu
from magenta.models.gansynth.lib import model as lib_model
from magenta.models.gansynth.lib import util
import matplotlib.pyplot as plt
import numpy as np
from numpy.lib import stride_tricks
from scipy import signal
from scipy.fft import fftshift
import tensorflow.compat.v1 as tf

absl.flags.DEFINE_string('ckpt_dir',
                         '/tmp/gansynth/acoustic_only',
                         'Path to the base directory of pretrained checkpoints.'
                         'The base directory should contain many '
                         '"stage_000*" subdirectories.')
absl.flags.DEFINE_integer('batch_size', 8, 'Batch size for generation.')
absl.flags.DEFINE_integer('pitch', None, 'Note pitch.')
absl.flags.DEFINE_integer('seed', None, 'Numpy random seed.')
absl.flags.DEFINE_string(
  "pca_file",
  None,
  "Path to file containing gansynth_ganspace PCA results."
)
absl.flags.DEFINE_string(
  "output_dir",
  None,
  "Output directory."
)
absl.flags.DEFINE_integer(
  "min",
  -1,
  "Minimum position."
)
absl.flags.DEFINE_integer(
  "max",
  1,
  "Maximum position."
)
absl.flags.DEFINE_integer(
  "steps",
  3,
  "Step count."
)
absl.flags.DEFINE_bool(
  "show",
  False,
  "Show plots after generating."
)

FLAGS = absl.flags.FLAGS
tf.logging.set_verbosity(tf.logging.INFO)

def batch(n, arr, pad):
  num = math.ceil(len(arr) / n)
  batches = []
  for i in range(0, num):
    l = i*n
    r = (i+1) * n
    batches.append(arr[l:r])
  while len(batches[-1]) < n:
    batches[-1].append(pad)
  return batches

""" short time fourier transform of audio signal """
def stft(sig, frameSize, overlapFac=0.5, window=np.hanning):
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # zeros at beginning (thus center of 1st window should be for sample nr. 0)   
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)    
    # cols for windowing
    cols = np.ceil( (len(samples) - frameSize) / float(hopSize)) + 1
    # zeros at end (thus samples can be fully covered by frames)
    samples = np.append(samples, np.zeros(frameSize))

    frames = stride_tricks.as_strided(samples, shape=(int(cols), frameSize), strides=(samples.strides[0]*hopSize, samples.strides[0])).copy()
    frames *= win

    return np.fft.rfft(frames)    

""" scale frequency axis logarithmically """    
def logscale_spec(spec, sr=44100, factor=20.):
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # create spectrogram with new freq bins
    newspec = np.complex128(np.zeros([timebins, len(scale)]))
    for i in range(0, len(scale)):        
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:        
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # list center freq of bins
    allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
    freqs = []
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            freqs += [np.mean(allfreqs[int(scale[i]):])]
        else:
            freqs += [np.mean(allfreqs[int(scale[i]):int(scale[i+1])])]

    return newspec, freqs

""" plot spectrogram"""
def plotstft(plt, samples, samplerate, binsize=2**10, plotpath=None, colormap="jet"):
    s = stft(samples, binsize)

    sshow, freq = logscale_spec(s, factor=1.0, sr=samplerate)

    ims = 20.*np.log10(np.abs(sshow)/10e-6) # amplitude to decibel

    timebins, freqbins = np.shape(ims)

    print("timebins: ", timebins)
    print("freqbins: ", freqbins)

    # plt.figure()
    plt.imshow(np.transpose(ims), origin="lower", aspect="auto", cmap=colormap, interpolation="none")
    # plt.figure.colorbar()

    plt.set_xlabel("time (s)")
    plt.set_ylabel("frequency (Hz)")
    plt.set_xlim([0, timebins-1])
    plt.set_ylim([0, freqbins])

    xlocs = np.float32(np.linspace(0, timebins-1, 5))
    plt.set_xticks(xlocs, ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate])
    ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
    plt.set_yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])

    # if plotpath:
    #     plt.savefig(plotpath, bbox_inches="tight")
    # else:
    #     plt.show()

    # plt.clf()

    return ims
  
def cartesian_product(*arrays):
  la = len(arrays)
  dtype = np.result_type(*arrays)
  arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
  for i, a in enumerate(np.ix_(*arrays)):
    arr[...,i] = a
  return arr.reshape(-1, la)

def format_float(x):
  return "{}".format(x).rstrip("0").rstrip(".")

def main(unused_argv):
  absl.flags.FLAGS.alsologtostderr = True
  
  # Load the model
  flags = lib_flags.Flags({'batch_size_schedule': [FLAGS.batch_size]})
  model = lib_model.Model.load_from_path(FLAGS.ckpt_dir, flags)

  # Make an output directory if it doesn't exist
  output_dir = util.expand_path(FLAGS.output_dir)
  if not tf.gfile.Exists(output_dir):
    tf.gfile.MakeDirs(output_dir)
  
  with open(FLAGS.pca_file, "rb") as fp:
    pca = pickle.load(fp)
      
  if FLAGS.seed != None:
    np.random.seed(seed=FLAGS.seed)
    tf.random.set_random_seed(FLAGS.seed)
    
  edits_axis = np.linspace(FLAGS.min, FLAGS.max, FLAGS.steps)
  edits_list = list(cartesian_product(edits_axis, edits_axis))
  
  pitch_arr = np.array([FLAGS.pitch])

  edits_batches = batch(FLAGS.batch_size, edits_list, [])
  pitch_batches = [[FLAGS.pitch]*FLAGS.batch_size]*len(edits_batches)

  fig, ax = plt.subplots(nrows=FLAGS.steps, ncols=FLAGS.steps, figsize=(15, 7.5))
  fig.set_tight_layout(True)
  
  def _plot():
    j = 0
    for edits_batch, pitch_batch in zip(edits_batches, pitch_batches):      
      waves = model.generate_samples_from_edits(pitch_batch, edits_batch, pca)
      
      for i, edits in enumerate(edits_batch):
        if j >= len(edits_list):
          return
        
        row = j // FLAGS.steps
        col = j % FLAGS.steps
        
        wave = waves[i]
        # wave = np.random.rand(64000)

        x = edits[0]
        y = edits[1]
        
        # plot wave
        subplot = ax[col][row]
        subplot.title.set_text("({}, {})".format(format_float(x), format_float(y)))
        plotstft(subplot, wave, 16000, binsize=2**8, colormap="magma")
        subplot.set_axis_off()

        # save wave
        gu.save_wav(wave, os.path.join(output_dir, "wave_{},{}.wav".format(x, y)))
        
        j += 1

  _plot()
  
  plt.savefig(os.path.join(output_dir, "plot.svg"), bbox_inches="tight")
  if FLAGS.show:
    plt.show()

  meta = [
    "checkpoint name: {}".format(os.path.basename(FLAGS.ckpt_dir)),
    "pca name: {}".format(os.path.basename(FLAGS.pca_file)),
    "pitch: {}".format(FLAGS.pitch),
    "min: {}".format(FLAGS.min),
    "max: {}".format(FLAGS.max),
    "steps: {}".format(FLAGS.steps)
  ]
  with open(os.path.join(output_dir, "meta.txt"), "w") as fp:
    fp.write("\n".join(meta) + "\n")
      
def console_entry_point():
  tf.app.run(main)

if __name__ == '__main__':
  console_entry_point()
