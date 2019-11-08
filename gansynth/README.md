# GANSynth: adversarial neural audio synthesis

GANSynth is an audio synthesis algorithm based on generative adversarial networks (GANs), introduced by Magenta in January 2019. Like the earlier NSynth algorithm, GANSynth is designed for generating musical notes at specified pitches, but GANSynth achieves better audio quality and also synthesizes thousands of times faster. The vastly improved speed makes the algorithm suitable for interactive purposes, potentially even near-real-time applications!

TODO: what is autoregressive, what does it do with sound, black box

Previously, autoregressive models like WaveNet (used in NSynth) represented the state of the art in neural audio synthesis. These models are good at learning the characteristics of sounds over very short time periods (local latent structure) but struggle with longer-term features (global latent structure). They are also very slow, since they have to generate waveforms one sample at a time.

In contrast, GANs are capable of modeling global latent structure, as well as synthesizing more efficiently. Since at least 2016, they have been used with great success to generate high-resolution images. However, Adapting GANs to audio generation has proven challenging due to their weakness at capturing local latent structure, producing sounds that lack phase coherence and thus don't sound very good. GANSynth tackles this problem by making several improvements to the network architecture and audio representation.

## Generative adversarial networks

Generative adversarial networks are a type of generative model where two neural networks — called *generator* and *discriminator* — compete against each other. The discriminator network tries to distinguish between real and generated data (e.g. images or audio samples), and is initially trained with a known data set. The generator network tries to produce data that the discriminator cannot tell apart from real data. During training, both networks become better at their respective tasks through backpropagation, resulting in a network that (hopefully) generates very realistic data.

A popular analogy for the generator-discriminator relationship is that of an art forger and investigator. The generator acts as a forger, trying to create convincing counterfeit pieces, while the discriminator acts as an investigator, trying to spot these counterfeits.

Often, the generator and discriminator network structures mirror each other. It is common to use a deconvolutional neural network (DNN) as generator and a convolutional neural network (CNN or ConvNet) as the discriminator.

TODO: diagram

## Architecture of GANSynth

The GANSynth network learns to represent timbre as vectors in a 512-dimensional latent space. It is also conditioned on a one-hot representation of pitch, to allow independent control of pitch and timbre in the synthesis process.

TODO: vectors and features

The generator synthesizes audio by sampling a random vector from the latent space according to a spherical Gaussian distribution, and running it through several layers of upsampling convolutions. The discriminator applies corresponding downsampling convolutions and produces an estimate of the divergence between the real and generated data. To encourage the network to make use of the pitch label, the discriminator also attempts to classify the pitch of the generated audio. The divergence estimate and pitch prediction error are combined to form the network's loss function, which is used for backpropagation during training.

The network operates on a spectral representation of audio rather than directly synthesizing waveforms. The full details can be found in the GANSynth paper, but the key elements of the representation are as follows: Magnitude and phase are computed using the short-time Fourier transform (STFT). The logarithm of the magnitude is taken to constrain its range, and the phase is unwrapped and differentiated to give a measure of "instantaneous frequency". Instantaneous frequency expresses the constant relationship between audio frequency and STFT frame frequency, addressing the phase coherence problem. The magnitude and instantaneous frequency are transformed to a mel frequency scale to achieve better separation of low frequencies.

## Exercises

1. Try generating some random latent vectors and synthesizing sounds from them using `gansynth.pd` and the `all_instruments` checkpoint. What kind of timbres does the neural network generate?
2. Try generating with the `acoustic_only` checkpoint instead (you may have to close and reopen the Pd patch). How do the results differ?
3. TODO: interpolation exercises? differences to NSynth? using our own trained checkpoints?

## Links

- [GANSynth: Adversarial Neural Audio Synthesis](https://openreview.net/forum?id=H1xQVn09FX) (paper)
- [Generative Adversarial Networks](https://arxiv.org/abs/1406.2661) (paper)
- [Progressive Growing of GANs for Improved Quality, Stability, and Variation](https://arxiv.org/abs/1710.10196) (paper)
- [Generative Adversarial Networks (GANs) - Computerphile](https://www.youtube.com/watch?v=Sw9r8CL98N0) (video)
- [Introduction to GANs, NIPS 2016 | Ian Goodfellow, OpenAI](https://www.youtube.com/watch?v=9JpdAg6uMXs) (video)
- [GANSynth](https://github.com/tensorflow/magenta/tree/master/magenta/models/gansynth) (code)

### Other audio/music applications of GANs

- [WaveGAN](https://github.com/chrisdonahue/wavegan) ([paper](https://github.com/chrisdonahue/wavegan), [web demo](https://chrisdonahue.com/wavegan/))
- [MuseGAN](https://salu133445.github.io/musegan/) ([paper]())
- [Conditional LSTM-GAN for Melody Generation from Lyrics](https://github.com/yy1lab/Lyrics-Conditioned-Neural-Melody-Generation) ([paper](https://arxiv.org/abs/1908.05551))a