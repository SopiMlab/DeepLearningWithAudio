# RAVE - Realtime Audio Variational autoEncoder

[RAVE](https://github.com/acids-ircam/RAVE) is another generative deep learning model for audio. This model has been introduced at the end of 2021 by Antoine Caillon and Philippe Esling. It allows fast and high-quality neural audio synthesis and is the first generative model that is able to generate 48kHz audio signals, while simultaneously running 20 times faster than real time on CPU level.  

The model is based on a VAE architecture and introduce a novel two stage training procedure:
- The first stage of the training permits to learn the representation of the audio by training a regular VAE. It learns to encode the original audio into a latent representation and then decode it, to reconstruct as perfect as possible. 
- Then, the second stage permits to fined-tune this VAE with an adversarial generation objective, in order to improve the synthesized audio quality and naturalness.

The overall training architecture is depicted in the following pictures:

![Rave Training Architecture](media/training-architecture-rave.png)



## Setup for real time generation in Pd (Linux)

Create the environment and install libtorch 1.10.1:

----
```
conda create -n rave_rt python=3.9
conda install pytorch==1.10.1 torchvision==0.11.2 torchaudio==0.10.1 cpuonly -c pytorch
```
----

Activate the environment:

```
conda activate rave_rt
```

Enter the rave directory in the course repository (in this example, located in the home directory):

```
cd ~/DeepLearningWithAudio/06_rave
```

Clone the nn~ repository for the external:

```
git clone https://github.com/acids-ircam/nn_tilde --recursive
```

Enter the resulting directory:

```
cd nn_tilde
```

Build the external:

```
mkdir build
cd build
cmake ../src/ -DCMAKE_PREFIX_PATH=/path/to/libtorch -DCMAKE_BUILD_TYPE=Release
make
```

__Note__: 
- It should be something like: `~/.conda_envs/lib/python3.8/site-packages/torch`.  
    

Copy the `nn~.pd_linux` into `~/Documents/Pd/extenals/`:
```
cp ./frontend/puredata/nn_tilde/nn~.pd_linux ~/Documents/Pd/extenals/
```

You can now open Puredata and use the nn~ object to generate sound in real time with a trained rave model. 

## Checkpoints

We have some pre-trained checkpoints in the [SOPI Google Drive](https://drive.google.com/drive/folders/1dapl3hR5SSGnzkc39LqD5vFyNVllWvA5).


## RAVE Training
See [Training RAVE](training/README.md).

## Links

- [RAVE: A variational autoencoder for fast and high-quality neural audio synthesis](https://arxiv.org/abs/2111.05011)
- [Streamable Neural Audio Synthesis With Non-Causal Convolutions](https://arxiv.org/abs/2204.07064)
