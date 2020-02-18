# Training GANSynth on Triton

This guide is supplemental to the [main training guide](../README.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

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
conda activate "$WRKDIR/conda/gansynth"
cd magenta
pip install -e .
```

If the last command complains about `oauth2client`, install a compatible version manually:

```
pip install 'oauth2client<4,>=2.0.1'
```

## Train

Prepare your dataset and copy the files to Triton, then submit a batch job using our `train.slrm` script. The script takes the following arguments:

1. Path to the Conda environment
2. Path to your training data file (`data.tfrecord`)
3. Path to your training metadata file (`meta.json`)
4. Path to the directory in which to save the trained model

It is best to submit the job from a fresh shell with no modules loaded and no Conda environment active, as an active environment may mess up some Python paths.

```
cd "$WRKDIR/DeepLearningWithAudio/gansynth/training/triton"
sbatch train.slrm "$WRKDIR/conda/gansynth" "$WRKDIR/mydataset/data.tfrecord" "$WRKDIR/mydataset/meta.json" "$WRKDIR/mymodel"
```
