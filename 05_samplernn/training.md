# Training SampleRNN

See also [PRiSM SampleRNN - Training](https://github.com/SopiMlab/prism-samplernn#training) for more details.

----

## Using Aalto computers

If you want to train on Aalto computers, see our [Using Aalto computers](../using-aalto-computers.md) document.

----

## Install SampleRNN

Follow the [instructions](README.md) to install PRiSM SampleRNN. You don't need `sopilib` or anything else from the `DeepLearningWithAudio` repository for training.

## Split audio into chunks

Note: before running `chunk_audio`, you should convert your audio to your desired sample rate (16000 Hz in this example) and mono. The `train` script is supposed to handle this automatically, but it seems to be buggy at the moment.

```
python -m samplernn_scripts.chunk_audio \
  --input_file path/to/input.wav \
  --output_dir ./chunks \
  --chunk_length 8000 \
  --overlap 1000
```

## Train

```
python -m samplernn_scripts.train \
  --id test \
  --data_dir ./data \
  --num_epochs 100 \
  --batch_size 128 \
  --checkpoint_every 5 \
  --output_file_dur 3 \
  --sample_rate 16000
```