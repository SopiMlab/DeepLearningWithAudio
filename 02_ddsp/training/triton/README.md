# DDSP training

This guide supplements the [main training guide](../README.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

## Set up the Conda environment

```
cd "$WRKDIR"
module -q load teflon
module -q load anaconda3
module -q load ffmpeg
```

If it is not done yet, clone the DeepLearningWithAudio repository:
```
git clone https://github.com/SopiMlab/DeepLearningWithAudio.git
```

```
conda env create -p "$WRKDIR/conda/ddsp" --file="$WRKDIR/DeepLearningWithAudio/utilities/dlwa/conda-env-specs/ddsp_linux-64.yml"
source activate "$WRKDIR/conda/ddsp"

cd "$WRKDIR/DeepLearningWithAudio/02_ddsp"
git clone https://github.com/magenta/ddsp.git
cd ddsp
pip install -e .
```


## Dataset

Your training dataset should have about 10-20 minutes of audio from your chosen instrument. The timbre transfer technique is designed for monophonic audio, but polyphonic recordings can also produce interesting results.

### Convert to TFRecord

Prepare your dataset and copy the files to Triton, then submit a batch job to convert the audio dataset to TFRecord dataset format by using our `ddsp_prepare_tfrecord.slrm` script.
In this example, we train on a single-file recording named `traveller_organ.wav`. 

It is best to submit the job from a fresh shell with no modules loaded and no Conda environment active, as an active environment may [mess up](https://version.aalto.fi/gitlab/AaltoScienceIT/triton/issues/612) some Python paths.


To submit a convert to TFRecord job, run:
```
sbatch $WRKDIR/DeepLearningWithAudio/02_ddsp/training/triton/ddsp_prepare_tfrecord.slrm \
    --conda_env "$WRKDIR/conda/ddsp" \
    -- \
    --alsologtostderr \
    --num_shards 10 \
    --sample_rate 16000 \
    --input_audio_filepatterns traveller_organ_16k.wav \
    --output_tfrecord_path traveller_organ_dataset/data.tfrecord
```

It is also possible to specify multiple files by passing a comma-delimited list, e.g.:

```
... --input_audio_filepatterns 'file1.wav,file2.wav,file3.wav' ...
```

Or a wildcard:

```
... --input_audio_filepatterns 'file*.wav' ...
```


## DDSP Training

When you have your TFRecord dataset, it is time to start your DDSP training. To submit a DDSP training, you can use our `ddsp_run.slrm` script.  

Run it as follows:

```
sbatch $WRKDIR/DeepLearningWithAudio/DeepLearningWithAudio/02_ddsp/training/triton/ddsp_run.slrm \
    --conda_env "$WRKDIR/conda/ddsp" \
    -- \
    --alsologtostderr \
    --mode=train \
    --save_dir=traveller_organ_train \
    --gin_file=models/solo_instrument.gin \
    --gin_file=datasets/tfrecord.gin \
    --gin_param="TFRecordProvider.file_pattern='traveller_organ_dataset/data.tfrecord*'" \
    --gin_param="batch_size=16" \
    --gin_param="train_util.train.num_steps=30000" \
    --gin_param="train_util.train.steps_per_save=300" \
    --gin_param="trainers.Trainer.checkpoints_to_keep=10"
```
