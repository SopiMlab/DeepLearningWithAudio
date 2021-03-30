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

## Exercises

