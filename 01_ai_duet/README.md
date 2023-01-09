# AI Duet (Melody RNN)

Melody RNN is a collection of models for generating melodies, introduced by Magenta in 2016. They apply language modeling with long short-term memory (LSTM) to music. These models operate on note data, rather than audio waveforms, and are relatively lightweight in terms of computational resources.

[AI Duet](https://experiments.withgoogle.com/ai-duet) by Yotam Mann is a web-based experiment in playing a duet together with the computer, using Melody RNN. We provide a Pure Data implementation of the building blocks of this idea, allowing it to be customized and incorporated into larger computer music systems.

### More on Melody RNN

- [Generating Long-Term Structure in Songs and Stories](https://magenta.tensorflow.org/2016/07/15/lookback-rnn-attention-rnn) (blog)
- [melody\_rnn](https://github.com/magenta/magenta/tree/master/magenta/models/melody_rnn) (code)

## Pre-trained models

Magenta provides a few [pre-trained models](https://github.com/magenta/magenta/tree/master/magenta/models/melody_rnn#pre-trained) to experiment with:

- [basic\_rnn](http://download.magenta.tensorflow.org/models/basic_rnn.mag)
- [mono\_rnn](http://download.magenta.tensorflow.org/models/mono_rnn.mag)
- [lookback\_rnn](http://download.magenta.tensorflow.org/models/lookback_rnn.mag)
- [attention\_rnn](http://download.magenta.tensorflow.org/models/attention_rnn.mag)

## Setup (macOS)

First make sure you have [pyext](../utilities/pyext-setup/) set up.

Make sure the Conda environment you used for pyext is activated:

```
conda activate magenta
```

Enter the `01_ai_duet` directory in the course repository. Assuming you downloaded the repository to your home directory:

```
cd ~/DeepLearningWithAudio/01_ai_duet
```

Download a pre-trained model (in this example, `attention_rnn`):

```
curl -LO http://download.magenta.tensorflow.org/models/attention_rnn.mag
```

if Command 'curl' not found, install it with'apt install' then download the pre-trained model

```
sudo apt install curl
```

You can now open `ai_duet.pd`! Note that it may take a while for the patch window to appear.

`ai_duet.pd` loads `attention_rnn` by default; modify the load message to use another model.
as
## Exercises

1. Experiment with two or more of the pre-trained models. How does their output differ?
