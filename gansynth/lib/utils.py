

def read_msg(stdin, size):
    msg = stdin.read(size)

    if not msg:
        raise EOFError("stdin")

    return msg