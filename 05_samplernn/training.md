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
  --sample_rate 16000 \
  --config_file path/to/my.config.json
```

## Example configuration files

We've had good results with linear quantization and skip connections enabled, using either LSTM or GRU (which one sounds better seems to depend on the dataset). Here are config files for these setups:

### `lstm-linear-skip.config.json`

```json
{
    "seq_len": 1024,
    "frame_sizes": [16,64],
    "dim": 1024,
    "rnn_type": "lstm",
    "num_rnn_layers": 4,
    "q_type": "linear",
    "q_levels": 256,
    "emb_size": 256,
    "skip_conn": true
}
```

### `gru-linear-skip.config.json`

```json
{
    "seq_len": 1024,
    "frame_sizes": [16, 64],
    "dim": 1024,
    "rnn_type": "gru",
    "num_rnn_layers": 4,
    "q_type": "linear",
    "q_levels": 256,
    "emb_size": 256,
    "skip_conn": true
}
```