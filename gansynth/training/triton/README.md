# Training GANSynth on Triton

This guide supplements the [main training guide](../README.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

## Set up the Conda environment

```
cd "$WRKDIR"
git clone https://github.com/SopiMlab/magenta.git
git clone https://github.com/SopiMlab/DeepLearningWithAudio.git
module load anaconda2/5.1.0-gpu
module load cuda/10.0.130
module load teflon
mkdir -p "$WRKDIR/conda"
conda create -p "$WRKDIR/conda/gansynth" python=3.7 tensorflow-gpu=1.15
source activate "$WRKDIR/conda/gansynth"
cd magenta
pip install -e .
```

If the last command complains about `oauth2client`, install a compatible version manually:

```
pip install 'oauth2client<4,>=2.0.1'
```

Likewise for `gym`:

```
pip install 'gym==0.14.0'
```

## Train

Prepare your dataset and copy the files to Triton, then submit a batch job using our `train2.slrm` script. The script requires the following arguments:

- Path to the Conda environment
- Path to your training data file (`data.tfrecord`)
- Path to your training metadata file (`meta.json`)
- Path to the directory in which to save the trained model

It is best to submit the job from a fresh shell with no modules loaded and no Conda environment active, as an active environment may [mess up](https://version.aalto.fi/gitlab/AaltoScienceIT/triton/issues/612) some Python paths.

```
cd "$WRKDIR/DeepLearningWithAudio/gansynth/training/triton"
```

For vanilla gansynth:

```
sbatch train2.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel"
```

For models/datasets with extra labels (here `nsynth_qualities_tfrecord`):

```
sbatch train2.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel" \ 
    --dataset_name nsynth_qualities_tfrecord
```