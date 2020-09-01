import sys

def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()

def read_msg(stdin, size):
    msg = stdin.read(size)

    if not msg:
        raise EOFError("stdin")

    return msg
