# DDSP Training on AzureVM

This guide is based on the DLWA script that aims to simplify usage of the models studied in the DeepLearningWithAudio course.  
For more information on how to use it, and on the organization of the directory, please take a look [here](../../utilities/dlwa).

---

Log in to https://labs.azure.com
(see the [login instructions](../../00_introduction/))

Enter the DLWA directory:
```
cd ~/DeepLearningWithAudio/utilities/dlwa
```

## Create a dataset
   
Your training dataset should have about 10-20 minutes of audio from your chosen instrument (violin, guitar...). The timbre transfer technique is designed for monophonic audio, but polyphonic recordings can also produce interesting results. Experiment!


### Transfer your files to the VM 

You can transfer your files from your own PC to the VM following the below command line structure.  
Open a new terminal window and make sure you are **in your own computer/laptop directory.**

* Transfer a folder

Let's assume that the folder you want to transfer is called: `violin`. The command line will be:

```
scp -P 4981 -r violin lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/inputs 
```

* Transfer a file

To transfert just a file, it is the same command line without the ```-r``` (-r = recursive).  
For example, if you want to transfer a file called: `violin.wav`, the command will be:
```
scp -P 4981 violin.wav lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/inputs
```

__Note__:

The number (**4981**) in the command line above should be changed with your personal info.
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))



### Convert to TFRecord

DDSP expects input in the TFRecord format, which is a generic file format for TensorFlow data. So, the WAV files need to be converted.  
To make the conversion, you can use the `make-dataset` command. 

Run it as follows:
```
./dlwa.py ddsp make-dataset --input_name violin --dataset_name myviolindataset 
```

It will look into the input directory `input/violin` and save the corresponding data.tfrecord files in the output directory `dataset/ddsp/myviolindataset`.

__Note__:
- *violin* and  *myviolindataset* should be replaced with your own folder names.
- By default, this command uses specific parameters. To modify these parameters, you can use the [custom and extra arguments](../../utilities/dlwa/README.md#custom-argument-extra-argument).  



## Starting the training  --- DLWA course ONLY --- 

Activate the dlwa-ddsp conda environemnt

```
conda activate dlwa-ddsp
```
Run the training with the `nohub` screening command:

```
nohup ddsp_run \
    --alsologtostderr \
    --mode=train \
    --save_dir=models/ddsp/myviolin_model \
    --gin_file=models/solo_instrument.gin \
    --gin_file=datasets/tfrecord.gin \
    --gin_param="TFRecordProvider.file_pattern='datasets/ddsp/myviolindataset/data.tfrecord*'" \
    --gin_param="batch_size=16" \
    --gin_param="train_util.train.num_steps=30000" \
    --gin_param="train_util.train.steps_per_save=300" \
    --gin_param="trainers.Trainer.checkpoints_to_keep=10" &
```
 

## Monitor the training --- DLWA course ONLY --- 

It is most likely that DDSP training will take approximatley 7 hours, during which you can log in and monitor the status of your training. To do that:

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
- If your **training still continues**, you will see similar output on your terminnal window:
```
I0413 06:28:29.788176 140451635803968 train_util.py:306] step: 25825    spectral_loss: 5.92     total_loss: 5.92  
I0413 06:28:31.960153 140451635803968 train_util.py:306] step: 25826    spectral_loss: 5.85     total_loss: 5.85  
I0413 06:28:34.149478 140451635803968 train_util.py:306] step: 25827    spectral_loss: 5.64     total_loss: 5.64  
I0413 06:28:36.336162 140451635803968 train_util.py:306] step: 25828    spectral_loss: 4.78     total_loss: 4.78 
```

You can detach the screen with pressing
**CTRL + C**


- If your **training is completed or ended with an error**, you will see the below text:
```
script failed: 
aborting
```

and kill the process if necessary
```
kill & 1
```


### Starting the training  --- for other AZURE VM ONLY --- 

Run the training with the `train` command:
```
./dlwa.py ddsp train --dataset_name your_name/myviolindataset --model_name your_name/myviolinmodel
```

This command line will start the DDSP training and save the checkpoints, logs and summaries in the `models/ddsp/your_name/myviolinmodel` directory.

__Note__:
- *your_name/myviolindataset* and *your_name/myviolinmodel* should be replaced with your own folder names.
- By default, this command uses specific parameters. If you want to go in details to customize your training, you can check them [here](../../utilities/dlwa/README.md#custom-argument-extra-argument).



### Monitor the training --- for other AZURE VM ONLY ---

It is most likely that DDSP training will take approximatley 17 hours, during which you can log in and monitor the status of your training. To do that:

Log in to https://labs.azure.com
(see the [login instructions](../../00_introduction/))

Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
./dlwa.py util screen-attach
```

- If your **training still continues**, you will see similar output on your terminnal window:
```
I0413 06:28:29.788176 140451635803968 train_util.py:306] step: 25825    spectral_loss: 5.92     total_loss: 5.92  
I0413 06:28:31.960153 140451635803968 train_util.py:306] step: 25826    spectral_loss: 5.85     total_loss: 5.85  
I0413 06:28:34.149478 140451635803968 train_util.py:306] step: 25827    spectral_loss: 5.64     total_loss: 5.64  
I0413 06:28:36.336162 140451635803968 train_util.py:306] step: 25828    spectral_loss: 4.78     total_loss: 4.78 
```

- If your **training is completed or ended with an error**, you will see the below text:
```
script failed: attach dlwa screen
aborting
```


## Transfer your trained model to your own laptop

You can transfer your files, such as trained models from the VM to your own laptop following the below command line structure.  
Open a new terminal window and **make sure you are in your own laptop directory**.  

* Transfer the folder of the trained model

```
scp -P 4981 -r lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:~/DeepLearningWithAudio/utilities/dlwa/models/ddsp/myviolinmodel ~/Downloads
```

__Note__:  
- The number (*4981*) in the command line above should be replaced with your personal number.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))
- *myviolinmodel* and *~/Downloads* should be replaced with your directory path in your own machine. 
