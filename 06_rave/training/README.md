# Training RAVE on Triton

This guide supplements the [official RAVE training guide](https://github.com/acids-ircam/RAVE/blob/master/docs/training_setup.md). It is assumed you have access to the [Triton](https://scicomp.aalto.fi/triton/) computing cluster and basic familiarity with how to run batch jobs there.

Start by login into Triton:
```
ssh username@triton.aalto.fi
```

## Set up the Conda environment

```
cd "$WRKDIR"
module load anaconda3
mkdir -p "$WRKDIR/conda"
conda create -p "$WRKDIR/conda/rave" python=3.9
source activate "$WRKDIR/conda/rave"
git clone https://github.com/SopiMlab/RAVE.git
cd RAVE
pip install -r requirements.txt
pip install protobuf==3.20.1
```


## Train

### Dataset

Prepare your dataset and copy the files to Triton.  
Before to start the training, take a look to the [preprocessing part](https://github.com/SopiMlab/RAVE#preprocessing), more detail [here](https://github.com/SopiMlab/RAVE/blob/master/docs/training_setup.md#about-the-dataset).

The authors of RAVE advise to have at least 3h of homogeneous recordings to train the model, more if the dataset is complex.  
It is possible to use audio files with different sampling rate and with a different extension (mp3, wav, flac...), you just need to use the `resample` utility in the folder where your files are located. 

```
conda activate rave
resample --sr TARGET_SAMPLING_RATE --augment
```

It will convert, resample, crop and augment all audio files present in the directory to an output directory called `out_TARGET_SAMPLING_RATE/` (which is the one you should give to `cli_helper_triton.py` when asked for the path of the .wav files).


### Preparation for the training

To obtain the insruction related to the training, you can use the `cli_helper_triton.py` script. 
You can run:

```
cd "$WRKDIR/RAVE"
python cli_helper_triton.py
```

It will ask for some parameters that you can change in the model (such as `batch_size`, `latent_dim`, `sampling_rate`...), and create a [text file](./instruction_modelname.txt) with the different command lines you will need to run to start the training. 


### Change the .slrm script to start the training

Because we want to start the training in Triton, we will need to change the .slrm script.

Open the instruction.txt file and copy the command line that correspond to the rave training, and past it in the [`train_rave.slrm`](./train_rave.slrm) in the triton directory.  
You can do the same for the prior training, copy the train command line and past it into the [`train_prior.slrm`](./train_prior.slrm) script in the triton directory. 


### Start rave training

Now that our slurm script are good to go, you can run the `train_rave.slrm` script:

```
cd "$WRKDIR/RAVE/triton"
sbatch train_rave.slrm --conda_env path/to/conda_env
```

When this training will be finished, you will need to export the model with `export_rave.py` before to start the prior training. (Like it is explained in the [instruction.txt](./instruction_modelname.txt))

```
cd "$WRKDIR/RAVE"
python export_rave.py --run triton/runs/magnatagatune_model/rave --cached false --name magnatagatune_model
```


### Start prior training

To start the prior training, you can run the `train_prior.slrm` script: 
```
cd "$WRKDIR/RAVE/triton"
sbatch train_prior.slrm --conda_env path/to/conda_env
```


### Export the final model

When the second training is finished, you can export the full model by following the last instruction of the [text file](./instruction_modelname.txt):

```
cd "$WRKDIR/RAVE"
python export_rave.py --run triton/runs/magnatagatune_model/rave --cached true --name magnatagatune_model_rt
python export_prior.py --run triton/runs/magnatagatune_model/prior --name magnatagatune_model_rt
python combine_models.py --prior prior_magnatagatune_model_rt.ts --rave rave_magnatagatune_model_rt.ts --name magnatagatune_model
```

It is now ready to be used in realtime in MaxMSP/Puredata.  
Many thanks to Antoine Caillon and Philippe Esling for this awesome work.