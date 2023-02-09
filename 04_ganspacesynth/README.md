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


## Computing GANSpaceSynth for THE DLWA COURSE !!!

Follow the instructions for [training GANSynth](../03_nsynth_and_gansynth/gansynth/training/README.md).

When you have a trained GANSynth model, you'll need to compute the PCA for GANSpaceSynth. To do this, use the `gansynth_ganspace` script: (replace `mymodel` with your trained checkpoint folder)

```
conda activate dlwa-gansynth
```
```
nohup gansynth_ganspace \
    --ckpt_dir models/gansynth/mymodel \
    --seed 0 \
    --layer conv0 \
    --random_z_count 8192 \
    --estimator ipca \
    --pca_out_file models/gansynth/mymodel/mymodel_conv0_ipca_8192.pickle &
```

You can also experiment with `--layer conv1` and larger values of `--random_z_count` (though the latter will increase the computation time).


### Monitor

It is most likely that GANSpaceSynth training will take approximatley 2 hours, during which you can log in and monitor the status of your training. To do that;

Log in to https://labs.azure.com
(see the [login instructions](../00_introduction/))

Enter the DLWA directory:
```
cd ~/DeepLearningWithAudio/utilities/dlwa
```

run the command:
```
tail -f nohup.out
```

- If your **training still continues**, you will see similar output on your termninal window :

```
I0412 14:37:21.286843 140283497939328 regression.py:49] regression batch 9/156
I0412 14:37:57.083486 140283497939328 regression.py:49] regression batch 10/156
I0412 14:38:32.043463 140283497939328 regression.py:49] regression batch 11/156
I0412 14:39:07.392691 140283497939328 regression.py:49] regression batch 12/156
```

- If your **training is completed, you will see the below text on your terminal window :

```
I0208 16:01:34.505822 139682987573632 gansynth_ganspace.py:244] saving PCA result to models/gansynth/Core23_model/Core23_model_conv0_ipca_8192.pickle
	adam_beta1: 0.0
	adam_beta2: 0.99
	audio_length: 64000
	batch_size_schedule: [8]
	d_fn: specgram
	data_normalizer: specgrams_prespecified_normalizer
	data_type: mel
	dataset_name: nsynth_tfrecord
	debug_hook: False
	discriminator_ac_loss_weight: 10.0
	discriminator_learning_rate: 0.0008
	fake_batch_size: 61
	fmap_base: 4096
	fmap_decay: 1.0
	fmap_max: 256
	g_fn: specgram
	gen_gl_consistency_loss_weight: 0.0
	generator_ac_loss_weight: 10.0
	generator_learning_rate: 0.0008
	gradient_penalty_target: 1.0
	gradient_penalty_weight: 10.0
	kernel_size: 3
	latent_vector_size: 256
	mag_normalizer_a: 0.0661371661726
	mag_normalizer_b: 0.113718730221
	master: 
	normalizer_margin: 0.8
	normalizer_num_examples: 1000
	num_resolutions: 7
	p_normalizer_a: 0.8
	p_normalizer_b: 0.0
	ps_tasks: 0
	real_score_penalty_weight: 0.001
	sample_rate: 16000
	save_graph_def: True
	save_summaries_num_images: 10000
	scale_base: 2
	scale_mode: ALL
	simple_arch: False
	stable_stage_num_images: 800000
	start_height: 2
	start_width: 16
	task: 0
	to_rgb_activation: tanh
	total_num_images: 11000000
	train_data_path: datasets/gansynth/Core23_dataset/data.tfrecord
	train_instrument_sources: [0]
	train_max_pitch: 84
	train_meta_path: datasets/gansynth/Core23_dataset/meta.json
	train_min_pitch: 24
	train_progressive: True
	train_root_dir: /home/lab-user/DeepLearningWithAudio/utilities/dlwa/models/gansynth/Core23_model
	train_time_limit: None
	train_time_stage_multiplier: 1.0
	transition_stage_num_images: 800000
Load model from /home/lab-user/DeepLearningWithAudio/utilities/dlwa/models/gansynth/Core23_model/stage_00012/model.ckpt-10346312
WARNING: Computed basis is not orthonormal (determinant=1.0031795825411387)
```


### Transfer your trained model to your own computer/laptop

You can transfer your files, such as trained models from the VM to your own laptop following the below command line structure.  
Open a new terminal window and make sure you are in your own computer/laptop directory.

- Transfer the ganspace.pickle file

```
scp -P 4981 lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/models/gansynth/mymodel/mymodel_conv0_ipca_8192.pickle ~/Downloads
```

__Note__:  
- The number (*4981*) in the command line above should be replaced with your personal number.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../00_introduction/))
- *mymodel* and *~/Downloads* should be replaced with your directory path in your own machine. 




## Exercises

1. Try loading some models & components into `ganspacessynth_noz.pd` and generate sounds by varying one direction at a time. What effects do the directions have?
2. Use HALLU (`ganspacesynth_halluseq.pd`) to create a hallucination composition moving through some parts of the latent space that you find interesting.


## !!! NOT FOR THE COURSE !!! -- Computing GANSpaceSynth on AzureVM for the AI-terity setup --

Follow the instructions for [training GANSynth](../03_nsynth_and_gansynth/gansynth/training/azure_training.md).

When you have a trained GANSynth model, you'll need to compute the PCA for GANSpaceSynth. To do this, use the below script: (replace `your_name/model` with your trained checkpoint folder)

```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
./dlwa.py gansynth ganspace --model_name your_name/model
```


