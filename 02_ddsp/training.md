# DDSP training

This guide describes how to train a DDSP timbre transfer model using your own sounds. Note that training is a very computation-intensive process, so you will want to use a powerful GPU.

----

## Using Aalto computers

If you want to train on Aalto computers, see our [Using Aalto computers](../using-aalto-computers.md) document.

----

## ffmpeg

You will need to have `ffmpeg` installed. On Aalto computers you can load this with Lmod using:

```
module load ffmpeg
```

Otherwise, install it from your package manager, e.g. on Ubuntu:

```
sudo apt install ffmpeg
```

## Conda environment

First make sure you have a Conda environment set up for DDSP — see our [main DDSP guide](README.md) (you can stop before the `sopilib` installation).

The DDSP package seems to have some issues with installing dependencies, and when trying to run the training scripts you may encounter errors like:

```
pkg_resources.ContextualVersionConflict: (six 1.12.0 (/scratch/other/sopi/conda/ddsp/lib/python3.7/site-packages), Requirement.parse('six>=1.13.0'), {'google-api-core'})
```

In this case, use `pip` to manually install the required package version (the one inside `Requirement.parse(...)`), e.g.:

```
pip install 'six>=1.13.0'
```

This has the potential to cause other incompatibilities, but in our experience it seems to work so far...

## Timbre transfer

### Dataset

Your training dataset should have about 10-20 minutes of audio from your chosen instrument. The timbre transfer technique is designed for monophonic audio, but polyphonic recordings can also produce interesting results. Experiment!

### Convert to TFRecord

In this example, we train on a single-file recording named `traveller_organ.wav`. 

Convert the audio to TFRecord dataset format:

```
ddsp_prepare_tfrecord \
    --alsologtostderr \
    --num_shards 10 \
    --sample_rate 16000 \
    --input_audio_filepatterns traveller_organ.wav \
    --output_tfrecord_path traveller_organ_dataset/data.tfrecord
```

It is also possible to specify multiple files by passing a comma-delimited list, e.g.:

```
... --input_audio_filepatterns 'file1.wav,file2.wav,file3.wav' ...
```

or a wildcard:

```
... --input_audio_filepatterns 'file*.wav' ...
```

### Train

Run the training:

```
ddsp_run \
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

### Save dataset statistics

Save dataset statistics (allows auto-adjusting parameters for better results when generating):

```
python DeepLearningWithAudio/02_ddsp/training/save_dataset_statistics.py \
    --tfrecord_file_pattern 'traveller_organ_dataset/data.tfrecord*' \
    --save_dir 'traveller_organ_train'
```

## Triton

(potentially outdated...)

```
module load teflon
module load anaconda3
module load ffmpeg
conda create -p /scratch/other/sopi/conda/ddsp python=3.8 tensorflow-gpu=2 tensorflow-probability
source activate /scratch/other/sopi/conda/ddsp
cd /scratch/other/sopi
git clone https://github.com/magenta/ddsp.git
cd ddsp
pip install -e .
cd ../ddsp-train-miranda
```

```
sbatch DeepLearningWithAudio/02_ddsp/training/triton/ddsp_prepare_tfrecord.slrm \
    --conda_env /scratch/other/sopi/conda/ddsp \
    -- \
    --alsologtostderr \
    --num_shards 10 \
    --sample_rate 16000 \
    --input_audio_filepatterns traveller_organ_16k.wav \
    --output_tfrecord_path traveller_organ_dataset/data.tfrecord
```

```
sbatch DeepLearningWithAudio/02_ddsp/training/triton/ddsp_run.slrm \
    --conda_env /scratch/other/sopi/conda/ddsp \
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