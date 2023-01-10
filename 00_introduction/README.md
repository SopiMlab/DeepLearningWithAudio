The course Deep Learning with Audio will introduce the state of the art in deep learning models applied to sound and music, with hands-on exercises on recent artificial intelligence (AI) implementations such as DDSP, AI-Duet, GANSynth, NSynth, GANSpaceSynth and SampleRNN. We will provide code templates that integrate the functionality from these open source deep learning audio projects into Pure Data programming environment. Students will be able to run, modify, access, control, input, output these deep learning models through Pure Data examples. Students will gain an understanding of the differences in input, computational cost and sonic characteristics between the different models, which will help formulate a course project. 

We will provide detailed setup instructions and automated scripts to make installation of the required tools as easy as possible (for Pure Data, Python, Conda, Magenta, PyExt). The current module of installations and course exercises only work in macOS and Linux, unfortunately Windows is not supported at the moment. You can contact https://takeout.aalto.fi and reserve a laptop computer for this course. 

Students will also learn and practice preparing data sets and traning deep learning models using cluster network in Aalto University. Students will further explore a particular model and incorporate it into their own project work. Deep Learning with Audio is a project-based course, we dedicate half of the contact hours for project work, the lecturer and the teaching assistants will support students by giving sufficient guidance, feedback and tutoring. At the end of the course, students will submit and present their projects.



## Installation of the Required Tools (Pure Data, Python, Conda, Magenta, PyExt)

First make sure you have [pyext](../utilities/pyext-setup/) set up.

----

## Registering Azure Lab Service 

Click on the __registration link__ that you received in your email.  
Once registered to the Azure Lab, you will be able to see the virtual machine for the lab you have access to.

To start/stop the VM:

- Click on the __Start__ button. This process takes some time, especially for the first time. After that, the machine will be running.
- Click on the __Connect__ button (small computer icon) to connect to the VM.  
When you log in for the first time you will be asked to set a password. It is a personal password, that you will have to enter every time you want to connect to the machine.

__Note:__  
To stop the VM, click on the same button as to start it.


## Student Azure Lab VM Log in 

In order to log in to Azure Lab, you need to [__remotely connect to Aalto University VPN network__](https://www.aalto.fi/en/services/establishing-a-remote-connection-vpn-to-an-aalto-network#6-remote-connection-to-students--and-employees--own-devices).


After you establish a VPN connection to Aalto university, you just need to go to https://labs.azure.com and __Log in__ with your aalto account.

After that, the ‘__DeepLearning With Audio Lab__’ course environment will appear under '__My virtual machines__' section:
- Click on the __Start__ button (if the machine is already running you do not need to).
- Click on the __Connect__ button (small computer icon), you will see a pop up with the ssh command line that you need to copy and paste into your terminal to connect to the VM, it looks like: 
```
ssh -p 4981 lab-user@lab-6e62099c-33a4-4d6c-951e-12c66dba5f9e.westeurope.cloudapp.azure.com
```

Open a __Terminal window__, paste the command line that you copied, click on enter and your password.

You are now in the __Deep Learning with Audio VM__.  

__Note:__  
If you have any problem with our instructions to connect to the VM, take a look to the official instructions:
- For registration [here](https://docs.microsoft.com/en-us/azure/lab-services/how-to-use-lab)
- To Connect to a Linux lab VM [here](https://docs.microsoft.com/en-us/azure/lab-services/connect-virtual-machine)
