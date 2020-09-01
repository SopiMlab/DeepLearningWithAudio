from __future__ import print_function

import os
import sys

import numpy as np

import sopilib.ddsp_protocol as protocol
from sopilib.utils import print_err, read_msg

from handlers import handlers

print_err("hello :)")

# open standard input/output handles

stdin = sys.stdin.buffer
stdout = sys.stdout.buffer

# write init message

stdout.write(protocol.to_tag_msg(protocol.OUT_TAG_INIT))
stdout.flush()

print_err("it begins @_@")

while True:
    in_tag_msg = read_msg(stdin, protocol.tag_struct.size)
    in_tag = protocol.from_tag_msg(in_tag_msg)
    
    if in_tag not in handlers:
        raise ValueError("unknown input message tag: {}".format(in_tag))

    handlers[in_tag](stdin, stdout)
