# Training SampleRNN on AzureVM

This guide is based on the DLWA script that aims to simplify usage of the models studied in the DeepLearningWithAudio course.  
For more information on how to use it, and on the organization of the directory, please take a look [here](../../utilities/dlwa).  

See also [PRiSM SampleRNN - Training](https://github.com/SopiMlab/prism-samplernn#training) for more details.

---

Log in to https://labs.azure.com
(see the [login instructions](../../00_introduction/))


Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
```

## Create a dataset

### Transfer your files to the VM 

Before transferring your files and running chunk_audio, you should convert your audio to your desired ***sample rate*** (16000 Hz by default) and ***mono***. The `train` script is supposed to handle this automatically, but it seems to be buggy at the moment.

You can transfer your files from your own PC to the VM following the below command line structure.  
Open a new terminal window and make sure you are in your own computer/laptop directory.

* Transfer a folder

Let's assume that the folder you want to transfer is called: `samplernn-inputs`. The command line will be:

```
scp -P 63635 -r samplernn_inputs lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name 
```

* Transfer a file

To transfert just a file, it is the same command line without the ```-r``` (-r = recursive).  
For example, if you want to transfer a file called: `samplernn.wav`, the command will be:
```
scp -P 63635 samplernn.wav lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name
```

__Note__:
- The number (*63635*) and *your_name* in the command line above should be changed with your personal info. 
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))



### Preparing your dataset

```
./dlwa.py samplernn chunk-audio --input_name your_name/samplernn-inputs --output_name your_name/samplernn-inputs_chunks
```

It will saves all the chunk files into `inputs/your_name/samplernn-inputs_chunks` (The folder `samplernn-inputs_chunks` will be automaticaly create with the command, don't need to create it before).

__Note__:
- *your_name/samplernn-inputs* and  *your_name/samplernn-inputs_chunks* should be replaced with your own folder names.
- By default, this command uses specific parameters to chunk the audio. To modify these parameters, you can use the [custom and extra arguments](../../utilities/dlwa/README.md#custom-argument-extra-argument).   



## Starting the training

```
./dlwa.py samplernn train --input_name your_name/samplernn-inputs_chunks --model_name  your_name/mysamplernnmodel  --preset lstm-linear-skip
```

This command line will start the SampleRNN training and will save the checkpoints and logs into `models/samplernn/your_name/mysamplernnmodel`. It will also save the generated audio into `generated/your_name/mysamplernnmodel`.


__Note__:
- *your_name/samplernn-inputs_chunks* and  *your_name/mysamplernnmodel* should be replaced with your own folder names.
- `--preset lstm-linear-skip` is the default choice with dlwa script.
- By default, this command uses specific parameters. For example, the default `sample rate` is specify as `16000Hz`, so if you want to use another sampling rate, you will need to use [custom parameters](../../utilities/dlwa/README.md#custom-argument-extra-argument).  



### Monitor the training

It is most likely that SampleRNN training will take approximatley 48 hours, during which you can log in and monitor the status of your training. To do that:

Log in to https://labs.azure.com (see the [login instructions](../../00_introduction/))


Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
./dlwa.py util screen-attach
```

- If your **training still continues**, you will see similar output on your termninal window:

```
Epoch: 27/100, Step: 6/250, Loss: 1.355, Accuracy: 46.000, (4.365 sec/step)
Epoch: 27/100, Step: 7/250, Loss: 1.352, Accuracy: 46.179, (4.377 sec/step)
Epoch: 27/100, Step: 8/250, Loss: 1.349, Accuracy: 46.208, (4.323 sec/step)
Epoch: 27/100, Step: 9/250, Loss: 1.344, Accuracy: 46.309, (4.358 sec/step)
```

- If your **training is completed**, you will see the below text on your terminal window:

```
script failed: attach dlwa screen
aborting! 
```


## Transfer your trained model to your own laptop

You can transfer your files, such as trained models from the VM to your own laptop following the below command line structure.  
Open a new terminal window and make sure you are in your own laptop directory.  

* Transfer a folder

```
scp -P 63635 -r lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com:/data/dome5132fileshareDeepLearningWithAudio/utilities/dlwa/models/samplernn/your_name/model_name ~/Downloads
```

__Note__:
- The number (*63635*) in the command line above should be changed with your personal info.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))
- *your_name/mysamplernnmodel* and *~/Downloads* should be replaced with your directory path in your own machine. 
