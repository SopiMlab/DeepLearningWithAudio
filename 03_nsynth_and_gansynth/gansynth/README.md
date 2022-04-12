# GANSynth: adversarial neural audio synthesis

GANSynth is an audio synthesis algorithm based on generative adversarial networks (GANs). It was introduced by Magenta in January 2019. Like the earlier NSynth algorithm, GANSynth is designed for generating musical notes at specified pitches, but GANSynth achieves better audio quality and also synthesizes thousands of times faster. The vastly improved speed makes the algorithm suitable for interactive purposes, potentially even near-real-time applications!

Previously, the state of the art in neural audio synthesis was represented by autoregressive models like WaveNet (used in NSynth). These models, which are based on predicting each sample based on some number of prior samples, are good at learning the characteristics of sounds over very short time periods (local latent structure) but struggle with longer-term features (global latent structure). They are also very slow, since they have to generate waveforms one sample at a time.

In contrast, GANs are capable of modeling global latent structure, as well as synthesizing more efficiently. Since at least 2016, they have been used with great success to generate high-resolution images. However, Adapting GANs to audio generation has proven challenging due to their weakness at capturing local latent structure, producing sounds that lack phase coherence and thus don't sound very good. GANSynth tackles this problem by making several improvements to the network architecture and audio representation.

Unlike NSynth, a trained GANSynth model is not able to take an arbitrary input sound and encode it into a latent representation. Instead, GANSynth provides a latent space of timbres that we have to navigate more or less at random. This exemplifies the typical black-box nature of deep neural networks: the model has learned some way of organizing the timbres it was trained on, but this organization is not easily understandable by humans. Somewhere in the latent space may be an area that corresponds to e.g. violin, but we don't have any easy way of finding that area.

Instead, we can pick random latent vectors until we find an interesting timbre. Given two (or more) different vectors, we can also interpolate between them to create in-between timbres.

## Generative adversarial networks

Generative adversarial networks are a type of generative model where two neural networks — called *generator* and *discriminator* — compete against each other. The discriminator network tries to distinguish between real and generated data (e.g. images or audio samples), and is initially trained with a known data set. The generator network tries to produce data that the discriminator cannot tell apart from real data. During training, both networks become better at their respective tasks through backpropagation, resulting in a network that (hopefully) generates very realistic data.

A popular analogy for the generator-discriminator relationship is that of an art forger and investigator. The generator acts as a forger, trying to create convincing counterfeit pieces, while the discriminator acts as an investigator, trying to spot these counterfeits.

Often, the generator and discriminator network structures mirror each other. It is common to use a deconvolutional neural network (DNN) as generator and a convolutional neural network (CNN or ConvNet) as the discriminator.

### More on GANs

- [Generative Adversarial Networks](https://arxiv.org/abs/1406.2661) (paper)
- [Progressive Growing of GANs for Improved Quality, Stability, and Variation](https://arxiv.org/abs/1710.10196) (paper)
- [Generative Adversarial Networks (GANs) - Computerphile](https://www.youtube.com/watch?v=Sw9r8CL98N0) (video)
- [Introduction to GANs, NIPS 2016 | Ian Goodfellow, OpenAI](https://www.youtube.com/watch?v=9JpdAg6uMXs) (video)

## Architecture of GANSynth

The GANSynth network learns to represent timbre as vectors in a 512-dimensional latent space. In practice this just means arrays containing 512 numbers. These vectors describe different sonic features found in the training dataset, though what exactly these features are can be difficult to analyze. The network is also conditioned on a one-hot representation of pitch, to allow independent control of pitch and timbre in the synthesis process.

The generator synthesizes audio by sampling a random vector from the latent space according to a spherical Gaussian distribution, and running it through several layers of upsampling convolutions. The discriminator applies corresponding downsampling convolutions and produces an estimate of the divergence between the real and generated data. To encourage the network to make use of the pitch label, the discriminator also attempts to classify the pitch of the generated audio. The divergence estimate and pitch prediction error are combined to form the network's loss function, which is used for backpropagation during training.

The network operates on a spectral representation of audio rather than directly synthesizing waveforms. The full details can be found in the GANSynth paper, but the key elements of the representation are as follows: Magnitude and phase are computed using the short-time Fourier transform (STFT). The logarithm of the magnitude is taken to constrain its range, and the phase is unwrapped and differentiated to give a measure of "instantaneous frequency". Instantaneous frequency expresses the constant relationship between audio frequency and STFT frame frequency, addressing the phase coherence problem. The magnitude and instantaneous frequency are transformed to a mel frequency scale to achieve better separation of low frequencies.

![Progressive GAN](media/progressive-gan.png)

*Diagram of Progressive GAN, which GANSynth is based on*

### More on GANSynth

- [GANSynth: Making music with GANs](https://magenta.tensorflow.org/gansynth) (blog, audio examples)
- [GANSynth: Adversarial Neural Audio Synthesis](https://openreview.net/forum?id=H1xQVn09FX) (paper)
- [GANSynth](https://github.com/tensorflow/magenta/tree/master/magenta/models/gansynth) (code)

### Other audio/music applications of GANs

- [WaveGAN](https://github.com/chrisdonahue/wavegan) ([paper](https://github.com/chrisdonahue/wavegan), [web demo](https://chrisdonahue.com/wavegan/))
- [MuseGAN](https://salu133445.github.io/musegan/) ([paper]())
- [Conditional LSTM-GAN for Melody Generation from Lyrics](https://github.com/yy1lab/Lyrics-Conditioned-Neural-Melody-Generation) ([paper](https://arxiv.org/abs/1908.05551))a

## Setup (macOS)

First ensure you have [pyext](../../utilities/pyext-setup/) set up.

Make sure the Conda environment you used for pyext is activated:

```
conda activate magenta
```

Enter the `gansynth` directory in the course repository. Assuming you downloaded the repository to your home directory:

```
cd ~/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth
```

Download a checkpoint (in this example, `all_instruments`):

```
curl -LO https://storage.googleapis.com/magentadata/models/gansynth/all_instruments.zip
```

Extract the zip:

```
unzip all_instruments.zip
```

Feel free to remove the zip file at this point.

Verify that GANSynth is working by generating some random notes:

```
gansynth_generate --ckpt_dir=all_instruments --output_dir=output
```

This will print a bunch of warnings, but should eventually produce a few wav files in the `output` subdirectory.

You can now run the patches:

- `gansynth.pd`
- `gansynth_multi.pd`
- `gansynth_hallucination.pd`

## Checkpoints

Google provides two [pre-trained neural networks](https://github.com/tensorflow/magenta/tree/master/magenta/models/gansynth#generation), called checkpoints: `all_instruments` is trained on all instruments in the NSynth dataset, while `acoustic_only` is trained on the acoustic instruments only.

We also have some of our own checkpoints available at the [SOPI Google Drive](https://drive.google.com/drive/folders/1yoJhvr2UY0ID3AP6jumUItJJGSkiBEg_).



## GANSynth Training in Azure My Virtual Machines

Log in to  https://labs.azure.com
(see the  [login instructions](https://github.com/SopiMlab/DeepLearningWithAudio/blob/master/00_introduction/))

c/p the command line below into your ternimnal window to go to the dlwa directory

```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa

```



**TRANSFERING YOUR DATASET**

You can transfer your files from your own PC to the vm following the below command line structure. Open a new terminal window make sure that you are in your own computer/laptop directory

transfering a folder

```
scp -P 63635 -r input_folder e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name 

```
transfering a file
```
scp -P 63635 input_name.wav e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name

```
Please note that the text **"63635"** in the command line above should be changed with your personal info. You can find it in the ssh command line in the pop up connect window. (see the  [login instructions](https://github.com/SopiMlab/DeepLearningWithAudio/blob/master/00_introduction/))

**input_folder** and should be replaced with your directory path in your own machine as well as the folder **your_name**. Please note that the name you give to **input_folder** will be used in below command lines as well.



**PREPARING YOUR DATASET**

```
./dlwa.py gansynth chop-audio --input_name your_name/input_folder_to_be_transferred --output_name your_name/mysounds_chopped
```
**your_name/input_folder** and  **your_name/mysounds_chopped** should be replaced with your own folder names. Saves chopped files into DeepLearningWithAudio/utilities/dlwa/inputs/mysounds_chopped (It will create the folder **mysounds_chopped**, don't need to create it before)

```
./dlwa.py gansynth make-dataset --input_name your_name/mysounds_chopped --dataset_name your_name/mysounds 
```
**your_name/mysounds_chopped ** and  **your_name/mysounds ** should be replaced with your own folder names. Saves data.tfrecord files into DeepLearningWithAudio/utilities/dlwa/datasets/gansynth/**your_name/mysounds**



**STARTING THE TRAINING**

```
/dlwa.py gansynth train --dataset_name your_name/mysounds --model_name your_name/model
```
**your_name/mysounds** and  **your_name/model** should be replaced with your own folder names. This command line will start the GANSynth training and and it will save trained checkpoints into DeepLearningWithAudio/utilities/dlwa/models/gansynth/**your_name/mysound** folder




## GANSynth training in other virtual machines

See [Training GANSynth](training/README.md).

## Exercises

1. Try generating some random latent vectors and synthesizing sounds from them using `gansynth.pd` and the `all_instruments` checkpoint. What kind of timbres does the neural network generate? How does the `acoustic_only` checkpoint compare?
2. Try manually drawing in the latent vector (z) array and then synthesizing. GANSynth expects z to be normalized such that its magnitude is 1, but drawing in arbitrary values breaks this. What happens to the generated sounds?
3. Try interpolating between different latent vectors using `gansynth_multi.pd`. How does the resulting synthesized sound compare to the sounds from the original latent vectors? By default, the `synthesize` message in this patch is set up to generate four different pitches, but it may be easier to compare sounds by using the same pitch for each.
4. (optional) Prepare your own dataset of sounds and [train](training/README.md) a new model.
