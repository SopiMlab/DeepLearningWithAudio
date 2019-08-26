from __future__ import print_function

"""This is an example script for the py/pyext object's basic functionality.

pyext Usage:
- Import pyext

- Inherit your class from pyext._class

- Specfiy the number of inlets and outlets:
    Use the class members (variables) _inlets and _outlets
    If not given they default to 1
    You can also use class methods with the same names to return the respective number

- Constructors/Destructors
    You can specify an __init__ constructor and/or an __del__ destructor.
    The constructor will be called with the object's arguments

    e.g. if your PD or MaxMSP object looks like
    [pyext script class arg1 arg2 arg3]

    then the __init__(self,*args) function will be called with a tuple argument
    args = (arg1,arg2,arg3) 
    With this syntax, you will have to give at least one argument.
    By defining the constructor as __init__(self,*args) you can also initialize 
    the class without arguments.

- Methods called by pyext
    The general format is 'tag_inlet(self,arg)' resp. 'tag_inlet(self,*args)':
        tag is the PD or MaxMSP message header.. either bang, float, list etc.
        inlet is the inlet (starting from 1) from which messages are received.
        args is a tuple which corresponds to the content of the message. args can be omitted.

    The inlet index can be omitted. The method name then has the format 'tag_(self,inlet,args)'.
    Here, the inlet index is a additional parameter to the method

    You can also set up methods which react on any message. These have the special forms
        _anything_inlet(self,*args)
    or
        _anything_(self,inlet,*args) 

    Please see below for examples.

    Any return values are ignored - use _outlet (see below).

    Generally, you should avoid method_, method_xx forms for your non-pyext class methods.
    Identifiers (variables and functions) with leading underscores are reserved for pyext.

- Send messages to outlets:
    Use the inherited _outlet method.
    You can either use the form
        self._outlet(outlet,arg1,arg2,arg3,arg4) ... where all args are atoms (no sequence types!)
    or
        self._outlet(outlet,arg) ... where arg is a sequence containing only atoms
        
    Do not use _outlet inside __init__, since the outlets have not been created at that time.

- Use pyext functions and methods: 
    See the __doc__ strings of the pyext module and the pyext._class base class.

"""

print("loading pd_magenta")
import sys

try:
    import pyext
except:
    print("ERROR: This script must be loaded by the PD/Max pyext external")

import os
import random
import time

import numpy as np
from magenta.models.gansynth.lib import flags as lib_flags
from magenta.models.gansynth.lib import generate_util as gu
from magenta.models.gansynth.lib import model as lib_model
from magenta.models.gansynth.lib import util
import tensorflow as tf

os.chdir(os.path.dirname(os.path.realpath(__file__)))

class gansynth(pyext._class):
    def __init__(self, *args):
        self._inlets = 1
        self._outlets = 1
        self._batch_size = 8
        self._model = None

    def load_1(self, ckpt_dir):
        ckpt_dir = str(ckpt_dir)
        flags = lib_flags.Flags({'batch_size_schedule': [self._batch_size]})
        self._model = lib_model.Model.load_from_path(ckpt_dir, flags)
        self._outlet(1, "loaded")

    def unload_1(self):
        if not self._model:
            raise Exception("can't unload - no model is loaded")
            
        self._model = None
        self._outlet(1, "unloaded")

    def randomize_z_1(self, buf_name):
        if not self._model:
            raise Exception("can't randomize z - no model is loaded")

        z = self._model.generate_z(1)[0]
        z32 = z.astype(np.float32)
        
        buf = pyext.Buffer(buf_name)
        if len(buf) != len(z32):
            buf.resize(len(z32))

        buf[:] = z32
        buf.dirty()

        self._outlet(1, "randomized")
        
    def synthesize_1(self, z_buf_name, audio_buf_name, pitch):
        if not self._model:
            raise Exception("can't synthesize - no model is loaded")

        z32_buf = pyext.Buffer(z_buf_name)
        z = np.array(z32_buf, dtype=np.float64)
        z_instruments = z.reshape((1,) + z.shape)        
        z_notes = z_instruments
        pitches = [pitch]
        audio_note = self._model.generate_samples_from_z(z_notes, pitches)[0]

        audio_buf = pyext.Buffer(audio_buf_name)
        if len(audio_buf) != len(audio_note):
            audio_buf.resize(len(audio_note))
        audio_buf[:] = audio_note
        audio_buf.dirty()
        
        self._outlet(1, "synthesized")
