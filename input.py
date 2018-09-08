import fcntl
import termios
import sys
import os
import time






import contextlib
import sys
from tqdm import tqdm




with NonBlockingInput():
    with tqdm(unit=' updates', file=sys.stdout, dynamic_ncols=True) as pbar:
        with contextlib.redirect_stdout(DummyTqdmFile(sys.stdout)):
            while True:
                c = sys.stdin.read(1)
                print('tick', c, '-', repr(c))
                #pbar.update()
                time.sleep(0.1)