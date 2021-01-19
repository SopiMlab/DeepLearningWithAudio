# Training GANSynth on Triton

This guide supplements the [main training guide](../README.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

## Set up the Conda environment

```
cd "$WRKDIR"
git clone https://github.com/SopiMlab/magenta.git
git clone https://github.com/SopiMlab/DeepLearningWithAudio.git
module load anaconda3
module load teflon
mkdir -p "$WRKDIR/conda"
conda create -p "$WRKDIR/conda/gansynth" python=3.8 tensorflow-gpu=2.2
source activate "$WRKDIR/conda/gansynth"
cd magenta
pip install --use-feature=2020-resolver -e .
```

## Train

Prepare your dataset and copy the files to Triton, then submit a batch job using our `train.slrm` script. The script requires the following arguments:

- Path to the Conda environment
- Path to your training data file (`data.tfrecord`)
- Path to your training metadata file (`meta.json`)
- Path to the directory in which to save the trained model

It is best to submit the job from a fresh shell with no modules loaded and no Conda environment active, as an active environment may [mess up](https://version.aalto.fi/gitlab/AaltoScienceIT/triton/issues/612) some Python paths.

```
cd "$WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/triton"
```

To submit a GANSynth training job, run:

```
sbatch train.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel"
```

TODO: how to compute PCA for GANSpaceSynth

To train with a dataset that has extra labels (here `nsynth_qualities_tfrecord`):

```
sbatch train.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel" \ 
    --dataset_name nsynth_qualities_tfrecord
```

(2020-11-17: this is still experimental and not really working...)