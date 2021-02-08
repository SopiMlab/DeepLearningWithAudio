# DDSP training

## Timbre transfer

```
ddsp_prepare_tfrecord \
    --input_audio_filepatterns traveller_organ.wav \
    --output_tfrecord_path traveller_organ_dataset/data.tfrecord
```

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

### Triton

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
sbatch ../DeepLearningWithAudio/ddsp/training/triton/prepare_tfrecord.slrm \
    --conda_env /scratch/other/sopi/conda/ddsp \
    --input_audio traveller_organ_16k.wav \
    --output_tfrecord_path traveller_organ_dataset/data.tfrecord    
```

```
sbatch ../DeepLearningWithAudio/ddsp/training/triton/train.slrm \
    --conda_env /scratch/other/sopi/conda/ddsp \
    --input_tfrecord_filepattern 'traveller_organ_dataset/data.tfrecord*' \
    --output_model_dir traveller_organ_train
```