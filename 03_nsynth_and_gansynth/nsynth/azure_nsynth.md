# Generating Audio with NSynth on AzureVM

This guide is based on the DLWA script that aims to simplify usage of the models studied in the DeepLearningWithAudio course.  
For more information on how to use it, and on the organization of the directory, please take a look [here](../../utilities/dlwa).

---

Log in to https://labs.azure.com
(see the [login instructions](../../00_introduction/))

Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
```


## Transfer your dataset to the VM

You can transfer your files from your own PC to the VM following the below command line structure.  
Open a new terminal window make sure you are in your own computer/laptop directory.

* Transfer a folder

Let's assume that the folder you want to transfer is called: `mynsynthdataset`. The command line will be:

```
scp -P 63635 -r myfolder e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name 
```

* Transfer a file

To transfert just a file, it is the same command line without the ```-r``` (-r = recursive).  
For example, if you want to transfer a file called: `myinput.wav`, the command will be:
```
scp -P 63635 myinput.wav e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/inputs/your_name
```

__Note__:
- The number (*63635*) and *your_name* in the command line above should be changed with your personal info.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))


## Preparing your dataset

```
./dlwa.py nsynth prepare --input_name your_name/mynsynthdataset --output_name your_name/nsynth
```

__Note__:
- *your_name/mynsynthdataset* and *your_name/nsynth* should be replaced with your own folder names.


## Starting generating Audio Samples

```
./dlwa.py nsynth generate --input_name your_name/nsynth --output_name your_name/nsynth --gpu 1
```

This command line will start generating the audio samples and will save it into `models/nsynth/your_name/nsynth` directory.

__Note__:
- *your_name/nsynth* and  *your_name/nsynth* should be replaced with your own folder names. 


### Monitor the generation of Audio Samples

To monitor the generation of Audio Samples:

Log in to  https://labs.azure.com
(see the  [login instructions](../../00_introduction/))

Enter the DLWA directory:
```
cd /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa
./dlwa.py util screen-attach
```

- If your **audio generation still continues**, you will see similar output on your termninal window :

```
/data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/outputs/nsynth/chouteau/nsynth/workdir/audio_output/batch0/gen_keyboardelectronic_0.047_organelectronic_0.596_pitch_60_reedacoustic_0.357.wav
I0413 13:17:32.301989 139917840717632 fastgen.py:175] Saving: /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/outputs/nsynth/chouteau/nsynth/workdir/audio_output/batch0/gen_keyboardelectronic_0.047_organelectronic_0.596_pitch_60_reedacoustic_0.357.wav
INFO:tensorflow:Saving: /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/outputs/nsynth/chouteau/nsynth/workdir/audio_output/batch0/gen_keyboardelectronic_0.047_organelectronic_0.596_pitch_64_reedacoustic_0.357.wav
I0413 13:17:33.942848 139917840717632 fastgen.py:175] Saving: /data/dome5132fileshare/DeepLearningWithAudio/utilities/dlwa/outputs/nsynth/chouteau/nsynth/workdir/audio_output/batch0/gen_keyboardelectronic_0.047_organelectronic_0.596_pitch_64_reedacoustic_0.357.wav
```

- If your **audio generation is completed**, you will see the below text on your terminal window :

```
script failed: attach dlwa screen
aborting
```


## Transfer your trained model to your own computer/laptop

You can transfer your files, such as trained models from your the virtual machine to your on own PC  following the below command line structure.  
Open a new terminal window make sure you are in your own computer/laptop directory.

* Transfer a folder

```
scp -P 63635 -r e5132-admin@ml-lab-00cec95c-0f8d-40ef-96bb-8837822e93b6.westeurope.cloudapp.azure.com:/data/dome5132fileshareDeepLearningWithAudio/utilities/dlwa/models/nsynth/your_name/nsynth ~/Downloads
```

__Note__:  
- The number (*63635*) in the command line above should be replaced with your personal number.  
You can find your own number in the ssh command line that you use to connect to the VM. (see the [login instructions](../../00_introduction/))
- *your_name/nsynth* and *~/Downloads* should be replaced with your directory path in your own machine. 