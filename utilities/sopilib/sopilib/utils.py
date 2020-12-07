import contextlib
import os
import os.path
import sys

def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()

def read_msg(stdin, size):
    msg = stdin.read(size)

    if not msg:
        raise EOFError("stdin")

    return msg

def sopimagenta_path(fn):
    # TODO: a less fragile solution
    diry = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sopimagenta/sopimagenta")
    path = lambda suf: os.path.join(diry, suf)
    d = {
        "gansynth_worker": path("gansynth/worker.py")
    }
    
    return d[fn]

@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as fnull:
        with contextlib.redirect_stdout(fnull) as out:
            yield out
