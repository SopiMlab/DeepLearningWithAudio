# Training GANSynth on AzureVM

This guide is based on the DLWA script that aims to simplify usage of the models studied in the DeepLearningWithAudio course.  
For more information on how to use it, and on the organization of the directory, please take a look [here](../../../utilities/dlwa).

---

Log in to https://labs.azure.com
(see the [login instructions](../../../00_introduction/))

Enter the DLWA directory:
```
cd ~/DeepLearningWithAudio/utilities/dlwa
```

## Create a dataset

### Transfer your files to the VM 

You can transfer your files from your own PC to the VM following the below command line structure.  
Open a new terminal window and make sure you are in your own computer/laptop directory.

* Transfer a folder

Let's assume that the folder you want to transfer is called: `mytunes`. The command line will be:

```
scp -P 4981 -r mytunes lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/inputs
```

* Transfer a file

To transfert just a file, it is the same command line without the ```-r``` (-r = recursive).  
For example, if you want to transfer a file called: `myfile.wav`, the command will be:
```
scp -P 4981 input_name.wav lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/inputs
```

__Note__:
- The number (*4981*) in the command line above should be changed with your personal info.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../../00_introduction/))


### Preparing your dataset

To chop up long files to the desired length and sampling rate (4s and 16000Hz for GANSynth), you can use the `chop-audio` command.  

Run it as follows:
```
./dlwa.py gansynth chop-audio --input_name mytunes --output_name mysounds_chopped
```

This will create suitable 4s chopped files in the `input/mysounds_chopped` directory (It will automaticaly create the folder `mysounds_chopped`, no need to create it before).

__Note__:
- *mytunes* and *mysounds_chopped* should be replaced with your own folder names.
- By default, this command line uses specific parameters. You can change them by adding extra arguments, see the documentation [here](../../../utilities/dlwa/README.md#custom-argument-extra-argument).



### Convert to TFRecord

GANSynth expects input in the TFRecord format (a generic file format for TensorFlow data), so the WAV files need to be converted. This can be done with our `make-dataset` command.

Run it as follows:

```
./dlwa.py gansynth make-dataset --input_name mysounds_chopped --dataset_name mydataset 
```

This command line will look into the directory `inputs/mysounds_chopped` and generate 2 files (`data.tfrecord` and `meta.json`) in the output directory `datasets/gansynth/mydataset`

__Note__:
- *mysounds_chopped* and  *mydataset* should be replaced with your own folder names. 
- By default, this command line uses specific parameters. You can modify them by adding extra arguments, see the documentation [here](../../../utilities/dlwa/README.md#custom-argument-extra-argument)


## Starting the training  --- DLWA course ONLY --- 

Activate the dlwa-gansynth conda environemnt

```
conda activate dlwa-gansynth
```
Run the training with the `nohub` screening command:

```
nohup gansynth_train \
    --config=mel_prog_hires \
    --hparams='{"train_data_path":"datasets/gansynth/mydataset/data.tfrecord", "train_meta_path":"datasets/gansynth/mydataset/meta.json", "train_root_dir":"models/gansynth/mymodel", "dataset_name":"nsynth_tfrecord"}' &
```
__Note__:
- *mydataset* and  *mymodel* should be replaced with your own folder names.


## Monitor the training --- DLWA course ONLY --- 

It is most likely that DDSP training will take approximatley 22 hours, during which you can log in and monitor the status of your training. To do that:

Log in to https://labs.azure.com
(see the [login instructions](../../00_introduction/))

Enter the DLWA directory:
```
cd ~/DeepLearningWithAudio/utilities/dlwa
```

run the command:
```
tail -f nohup.out
```
- If your **training still continues**, you will see similar output on your terminal window:
```
I0409 16:32:56.410543 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 184, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.123 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 192, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.105 sec)
I0409 16:32:56.515631 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 192, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.105 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 200, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
I0409 16:32:56.627448 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 200, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 208, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
I0409 16:32:56.739801 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 208, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec) 
```

- If your **traning is completed or ended with an error**, you will see the below text:
```
script failed:
aborting
```

You can detach the screen with pressing
**CTRL + C**


- If your **training is completed or ended with an error**, you will see the below text:
```
script failed: attach dlwa screen
aborting
```

and kill the process if necessary
```
kill & 1
```


### Starting the training  --- Azure VM ONLY ---

Run the training with the `train` command:
```
./dlwa.py gansynth train --dataset_name your_name/mydataset --model_name your_name/mymodel
```

This command line will start the GANSynth training. It will load the training data that is stored in the 2 files, `data.tfrecord` and `meta.json`, and generate checkpoints in the `gansynth/your_name/mymodel` directory

__Note__:
- *your_name/mydataset* and  *your_name/mymodel* should be replaced with your own folder names.


### Monitor the training  --- Azure VM ONLY ---

It is most likely that GANSynth training will take approximatley 48 hours, during which you can log in and monitor the status of your training. To do that:

Log in to https://labs.azure.com
(see the [login instructions](../../../00_introduction/))


Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
./dlwa.py util screen-attach
```

- If your **training still continues**, you will see similar output on your terminal window:
```
I0409 16:32:56.410543 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 184, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.123 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 192, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.105 sec)
I0409 16:32:56.515631 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 192, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.105 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 200, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
I0409 16:32:56.627448 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 200, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
INFO:tensorflow:Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 208, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec)
I0409 16:32:56.739801 140269805838720 basic_session_run_hooks.py:260] Tensor("status_message:0", shape=(), dtype=string) = b'Starting train step: current_image_id: 208, progress: 0.000000, num_blocks: 1, batch_size: 8' (0.112 sec) 
```

- If your **traning is completed or ended with an error**, you will see the below text:
```
script failed: attach dlwa screen
aborting
```

## Transfer your trained model to your own laptop

You can transfer your files, such as trained models from the VM to your own laptop following the below command line structure.  
Open a new terminal window and make sure you are in your own laptop directory.  

* Transfer the folder of the trained model
```
scp -P 4981 -r lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/models/gansynth/mymodel ~/Downloads
```

__Note__:  
- The number (*4981*) in the command line above should be changed with your personal number.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the  [login instructions](../../../00_introduction/))
- *mymodel* and *~/Downloads* should be replaced with your directory path in your own machine. 
