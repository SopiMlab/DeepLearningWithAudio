# GANSpaceSynth

Magenta's [GANSynth](https://magenta.tensorflow.org/gansynth) produces novel sounds, but offers limited control of the generation process. The user can specify pitch, but timbre is determined by a latent vector in a high-dimensional space that is challenging to navigate.

It is possible to sample random latent vectors to obtain a variety of timbres, and to interpolate between them to morph from one timbre to another. We look into some ways to allow more human input into the generation.

## Hallucinations

For the hallucination project, we wanted to use GANSynth to generate hallucinatory audio effects similar to what has been made with other GAN models in the image domain. The implementation was relatively simple, because the GANSynth repository already had examples of how to randomly sample the latent space and how to interpolate between these points. So using these examples, we implemented the hallucinations as follows.

First the latent space is sampled randomly `n` times to get the key points which the hallucination will travel through. Then for each consecutive key point, we interpolate between them using spherical linear interpolation taking `m` samples at even spacings. We then generate the audio for all the sampled points using a GANSynth model, resulting in `n + (n - 1)m` audio samples. Then we apply an envelope to each samples independently. Finally we merge the samples, placing them so that consecutive samples overlap slightly, resulting in the final hallucination.

How good the generated hallucinations sound depends greatly on the data the GANSynth model was trained on. Using the NSynth dataset resulted in hallucinations which aren't very interesting, mainly because the dataset consists of single notes. 

After finishing the implementation, we spent the rest of the time training GANSynth models on different custom datasets to find what kind of models generated the nicest hallucinations. The initial problem we faced was the it takes a lot of effort to create a good quality dataset to train GANSynth on. We ended up deciding to take the easy way out by creating a Python script that takes longer audio tracks and simply splits them into 4 second samples. 

One of the best sounding once was trained on classical guitar music. The generated hallucinations sounded very similar to the original tracks while still being original.
Another good one was trained on ambient music.

## Conditional GANSynth

GANSynth's pitch control works by adding a pitch label to the input of the generator network, as well as a pitch classification output and associated auxiliary loss function to the discriminator. Samples in the training dataset are annotated with pitch values. Through this *conditioning* the GAN learns to manipulate pitch independently from timbre.

As our first experiment, we extend the conditioning idea by adding similar labels for other properties. The [NSynth](https://magenta.tensorflow.org/datasets/nsynth) training dataset is annotated with features such as [instrument sources](https://magenta.tensorflow.org/datasets/nsynth#instrument-sources), [instrument families](https://magenta.tensorflow.org/datasets/nsynth#instrument-families) and [note qualities](https://magenta.tensorflow.org/datasets/nsynth#note-qualities), so we modify GANSynth to use these. Members of the Magenta team confirm to us that this seems like a reasonable approach, but question whether GANSynth can learn such high-level semantic characteristics.

Changes are needed in several parts of the codebase. In the interest of modularity, we modify the model code to work with a generic condition definition architecture that bundles the modifications in a self-contained way. 

In the dataset traversal code, we expose the relevant feature annotations. Mimicking the existing pitch conditioning code, we add additional labels to the generator's input by providing placeholder tensors and a statistical distribution of labels based on their prevalence in the dataset.

In the discriminator, we add as a classification endpoint a dense layer matching the number of labels for each condition. To the auxiliary classification loss function, we add a measure of the classification error.

So far, we were unable to get any conclusive results. Our trained models tended to generate noise or very limited timbres, even when we tried to reproduce the original training (pitch conditioning only) using our code. This seems to suggest we still have bugs to fix.

## GANSpaceSynth

[GANSpace](https://arxiv.org/abs/2004.02546) presents a simple method to discover editable features in existing image GANs. By computing a principal component analysis (PCA) of the activations in early layers of the network (for lots of random input vectors), the authors discover significant directions in the latent space. The directions map to a variety of semantic image features, such as viewpoint, aging and lighting.

In GANSpaceSynth, we apply the GANSpace technique to GANSynth. GANSpace hooks into the early GAN layers using [NetDissect](http://netdissect.csail.mit.edu/), which is designed for PyTorch neural networks, but GANSynth is based on TensorFlow. Thus we can't use the GANSpace code directly and instead implement a hook mechanism using TensorFlow placeholders to inject offset values into the layers.

We sample random latent vectors, feed them into GANSynth and compute a PCA of the activations on the first two convolution layers, `conv0` and `conv1`. The output shape of these layers is (2, 16, 256), i.e. a total of 8192 values. we use [incremental PCA](https://scikit-learn.org/stable/auto_examples/decomposition/plot_incremental_pca.html) to compute in batches and limit memory consumption.

In initial experiments with Magenta's `all_instruments` checkpoint, on layer `conv0` and with 4,194,304 samples, the PCA does clearly reveal some significant latent directions, but ascribing semantic meaning to these is difficult. The first direction seems to be related to note sustain length, but there is some entanglement with other timbral characteristics.

==results, Pd patches...==

More experimentation is needed with different trained models, sample counts, layers etc.

## Setup

Make sure you have [pyext](../utilities/pyext-setup) and [GANSynth](../03_nsynth_and_gansynth/gansynth) set up. You can then open the `.pd` patches.



## Training GANSpaceSynth in Azure My Virtual Machines

Follow the instructions for [training GANSynth](../03_nsynth_and_gansynth/gansynth/training/README.md).

When you have a trained GANSynth model, you'll need to compute the PCA for GANSpaceSynth. To do this, use the below script: (replace **your_name/model** with your trained checkpoint folder)

```
./dlwa.py gansynth ganspace --model_name your_name/model
```


**MONITORING THE TRAINING**

It is most likely that GANSpaceSynth training will take approximatley 2 hours, during which you can log in and monitor the status of your training. To do that;

Log in to  https://labs.azure.com
(see the  [login instructions](https://github.com/SopiMlab/DeepLearningWithAudio/blob/master/00_introduction/))

c/p the command line below into your ternimnal window to go to the dlwa directory

```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
```

```
./dlwa.py util screen-attach
```

If your **traning still continues**, you will see similar output on your termninal window :

```
I0412 14:37:21.286843 140283497939328 regression.py:49] regression batch 9/156
I0412 14:37:57.083486 140283497939328 regression.py:49] regression batch 10/156
I0412 14:38:32.043463 140283497939328 regression.py:49] regression batch 11/156
I0412 14:39:07.392691 140283497939328 regression.py:49] regression batch 12/156
```

If your **traning is completed**, you will see the below text on your terminal window :

```
script failed: attach dlwa screen
aborting
```



**TRANSFERING YOUR TRAINED MODEL TO YOUR OWN COMPUTER/LAPTOP**

You can transfer your files, such as trained models from your the virtual machine to your on own PC  following the below command line structure. Open a new terminal window make sure that you are in your own computer/laptop directory.

* Transfering a folder

```
scp -P 63635 e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshareDeepLearningWithAudio/utilities/dlwa/models/gansynth/your_name/mysound/ganspace.pickle ~/Downloads
```

Please note that the text **"63635"** in the command line above should be changed with your personal info. You can find it in the ssh command line in the pop up connect window. (see the  [login instructions](https://github.com/SopiMlab/DeepLearningWithAudio/blob/master/00_introduction/))

**your_name/mysound** and should be replaced with your directory path in your own machine. 



## Training GANSpaceSynth without dlwa

Follow the instructions for [training GANSynth](../03_nsynth_and_gansynth/gansynth/training/README.md).

When you have a trained GANSynth model, you'll need to compute the PCA for GANSpaceSynth. To do this, use the `gansynth_ganspace` script: (replace `mymodel` with your trained checkpoint folder)

```
conda activate dlwa-gansynth

gansynth_ganspace \
    --ckpt_dir mymodel \
    --seed 0 \
    --layer conv0 \
    --random_z_count 4194304 \
    --estimator ipca \
    --pca_out_file mymodel/mymodel_conv0_ipca_4194304.pickle
```

You can also experiment with `--layer conv1` and larger values of `--random_z_count` (though the latter will increase the computation time).





## Exercises

1. Try loading some models & components into `ganspacessynth_noz.pd` and generate sounds by varying one direction at a time. What effects do the directions have?
2. Use HALLU (`ganspacesynth_halluseq.pd`) to create a hallucination composition moving through some parts of the latent space that you find interesting.
