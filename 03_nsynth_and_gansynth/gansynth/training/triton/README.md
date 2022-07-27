# Training GANSynth on Triton

This guide supplements the [main training guide](../README.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

## Set up the Conda environment

```
cd "$WRKDIR"
git clone https://github.com/SopiMlab/magenta.git
git clone https://github.com/SopiMlab/DeepLearningWithAudio.git
module -q load anaconda3
mkdir -p "$WRKDIR/conda"
conda env create -p "$WRKDIR/conda/gansynth" --file="$WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/gansynth-training-env.yml"

source activate "$WRKDIR/conda/gansynth"
cd magenta
pip install -e .
```

### Protobuf Workaround

```
cd $WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training
mkdir repos 
cd repos
git clone --branch v3.13.0 https://github.com/protocolbuffers/protobuf.git
cd protobuf
git submodule update --init --recursive
./autogen.sh
cd python
python setup.py build
conda remove --yes --force protobuf libprotobuf
python setup.py develop
```

## Creation of a dataset

Let's assume that you want to create a dataset in your `WRKDIR` directory:
```
cd "$WRKDIR"
```

Create a folder and put all your WAV files in it.  
__e.g:__
```
wget "https://dl.dropboxusercontent.com/s/0qn8nsh0ljym7dl/samples.zip?dl=0"
mv samples.zip\?dl=0 samples.zip 
unzip samples.zip
```

To chop up long files to the desired length and sample rate (4s and 16000Hz for GANSynth), you can use the `chop.py` script.  

Run it as follows:
```
python $WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/chop.py --step 16000 samples mysampleschopped
```

__Argument to add if necessary:__  
- `--sample_rate` -> default=16000  
- `--len` -> default=64000  
- `--step` -> default=64000  
- `--pitch` -> default=32  

This command line will create suitable 4s chopped files in the `$WRKDIR/mysampleschopped` directory.  
 
### Convert to TFRecord 

GANSynth expects input in the TFRecord format (a generic file format for TensorFlow data), so the WAV files need to be converted. This can be done with our `make_dataset.py` script:
```
python $WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/make_dataset.py --in_dir mysampleschopped --out_dir mydataset
```

__Argument to add if necessary:__  
- `--out_dir` : the folder will be created by the script, so don't create it before  
- `--sample_rate` -> default=16000  
- `--length` -> default=64000  


The script will generate 2 files (`data.tfrecord` and `meta.json`) in the `$WRKDIR/mydataset` directory. You will need them later.

## Train

### GANSynth Training

When your dataset is ready, submit a batch job using our `train.slrm` script. The script requires the following arguments:

- Path to the Conda environment
- Path to your training data file (`data.tfrecord`)
- Path to your training metadata file (`meta.json`)
- Path to the directory in which to save the trained model

It is best to submit the job from a fresh shell with no modules loaded and no Conda environment active, as an active environment may [mess up](https://version.aalto.fi/gitlab/AaltoScienceIT/triton/issues/612) some Python paths.

To submit a GANSynth training job, enter the triton directory:
```
cd "$WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/triton"
```
And run:
```
sbatch train.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel"
```

__Note:__  
If you want to change the config file for training parameters, like batch size, num_trans_images... just go to: 
```
cd $WRKDIR/magenta/magenta/models/gansynth/configs
vim mel_prog_hires.py
```  
And modify the parameters you want:  
 + To change something on vim, you need to be in `--insert--` mode ! Type `i` to enter this mode. 
 + To save your changes, it is `:x` | to exit `:q` | to exit without saving changes `:q!`
<br/><br/>

__Note bis:__  
If you want to change the length of the generated audio. You have to modify 2 scripts:  
+ [`dataset.py`](https://github.com/SopiMlab/magenta/blob/master/magenta/models/gansynth/lib/datasets.py#L98) in the magenta folder (`magenta/magenta/models/gansynth/lib/dataset.py`), to modify the audio length in the dataset (line 98)
+ [`train.slrm`](https://github.com/SopiMlab/DeepLearningWithAudio/blob/master/03_nsynth_and_gansynth/gansynth/training/triton/train.slrm#L72), to modify the audio length parameter (line 72)  
<br/><br/>

To train with a dataset that has extra labels (here `nsynth_qualities_tfrecord`):

```
sbatch train.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --train_data_path "$WRKDIR/mydataset/data.tfrecord" \
    --train_meta_path "$WRKDIR/mydataset/meta.json" \
    --train_root_dir "$WRKDIR/mymodel" \ 
    --dataset_name nsynth_qualities_tfrecord
```

### PCA for GANSpaceSynth

To compute PCA for GANSpaceSynth, you can submit a batch job using our `ganspace.slrm` script. The script requires the following arguments:

- Path to the Conda environment
- Path to the directory in which is located your GANSynth model


Run it as follows:
```
cd "$WRKDIR/DeepLearningWithAudio/03_nsynth_and_gansynth/gansynth/training/triton"
```
```
sbatch ganspace.slrm \
    --conda_env "$WRKDIR/conda/gansynth" \
    --ckpt_dir "$WRKDIR/mymodel"
```
