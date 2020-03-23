# DDSP

DDSP (Differentiable Digital Signal Processing) is a library for generating audio through a combination of standard DSP techniques and deep learning, introduced by Magenta in January 2020. Instead of directly generating audio samples or frequency spectra, DDSP's approach is to provide a library of DSP elements (oscillators, filters, reverbs...) implemented as differentiable functions, allowing them to be used as components of deep learning models that are trained with backpropagation and gradient descent.

In a DDSP model, the neural network is tasked with generating parameters for the DSP elements, which then synthesize or process audio according to these parameters. Since the behavior of standard DSP elements is well understood, this allows greater interpretability (understanding how the model operates) compared to the typical black-box nature of deep learning models.

## Timbre transfer

DDSP is a very general toolkit and probably has lots of potential applications still to be discovered. One of the first examples showcased by the Magenta team is timbre transfer. A DDSP model is trained on 10-20 minutes of audio from an instrument and learns a representation of the instrument's timbre, which can then be transferred to other input audio. For example, a sung melody can be turned into violin.

The model works by trying to reconstruct sounds from the training dataset using spectral modeling synthesis. Spectral modeling synthesis (also known as harmonics plus noise model) combines a harmonic additive oscillator and a filtered noise generator, both varying in time to synthesize complex timbres.

The input audio is divided into short frames, and three encoders produce latent representations of fundamental frequency, loudness and timbre information. These are fed into a decoder, which translates the latent representations into parameters for the additive oscillator and filtered noise. Finally, the summed signal from these is optionally passed through a convolution reverb. In the examples, the reverb impulse response is fixed, but it could in principle be learned from the training dataset!

## Setup

```
conda create -n ddsp python=3.7 tensorflow=2.1
git clone https://github.com/magenta/ddsp.git
cd ddsp
pip install -e .
```

## Magenta's checkpoints

```
https://storage.googleapis.com/ddsp/models/tf2/solo_violin_ckpt.zip
https://storage.googleapis.com/ddsp/models/tf2/solo_flute_ckpt.zip
https://storage.googleapis.com/ddsp/models/tf2/solo_flute2_ckpt.zip
```