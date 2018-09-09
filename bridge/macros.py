import logging

from .state import State

logger = logging.getLogger(__name__)

class MacroManager(object):
    def __init__(self, states, macrosfilename=None, globalrecfilename=None):
        self.states = states
        self.macros = {}

        self.recordmacro = None
        self.recordfile = None

        self.playmacro = None
        self.playiter = None

        self.globalrecfile = None
        if globalrecfilename is not None:
            self.globalrecfile = open(globalrecfilename, 'wb')

        if macrosfilename is not None:
            with open(macrosfilename) as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    line = line.strip().split()
                    if len(line) == 3:
                        self.macros[line[0]] = (line[1], line[2], State.all())
                    if len(line) == 4:
                        self.macros[line[0]] = (line[1], line[2], State.fromhex(line[3]))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.record_stop()
        self.play_stop()

    def log_macro_event(self, event, macro):
        logger.info('{:s} macro {:s} : {:s}({:s}), mask: {:s}'.format(
                event, macro, self.macros[macro][0],
                self.macros[macro][1],
                self.macros[macro][2].hexstr
        ))

    def record_start(self, macro):
        if self.recordfile is None:
            if self.playmacro == macro:
                self.play_stop()
            if self.macros[macro][0] in ['file', 'fileloop']:
                self.recordmacro = macro
                self.recordfile = open(self.macros[macro][1], 'wb')
                self.log_macro_event('Recording to', macro)
            else:
                logger.error('Key {:s} is not bound to a file macro. Can\'t record.'.format(macro))
        elif self.recordmacro == macro:
            self.record_stop()
        else:
            logger.error('Already recording a macro.')

    def record_stop(self):
        if self.recordfile is not None:
            self.recordfile.close()
            self.recordfile = None
            self.log_macro_event('Stopped recording to', self.recordmacro)
            self.recordmacro = None

    def play_start(self, macro):
        if self.recordmacro == macro:
            self.record_stop()
            return
        if self.playiter is not None:
            if self.playmacro == macro:
                self.play_stop()
                return
            else:
                self.play_stop()
        self.playmacro = macro
        self.playiter = macro_funcs[self.macros[macro][0]](self.macros[macro][1])
        self.log_macro_event('Playing', self.playmacro)

    def play_stop(self):
        if self.playiter is not None:
            self.playiter.close()
            self.playiter = None
            self.log_macro_event('Stopped playing', self.playmacro)
            self.playmacro = None

    def key_pressed(self, k):
        if len(k) != 1:
            return
        if k in self.macros:
            self.play_start(k)
        elif k.lower() in self.macros:
            self.record_start(k.lower())
        else:
            logger.error('Key "{:s}" is not bound to a macro. Ignored.'.format(k.lower()))

    def __iter__(self):
        return self

    def __next__(self):
        n = next(self.states)
        if self.playiter is not None:
            try:
                m = next(self.playiter)
                mask = self.macros[self.playmacro][2]
                n = (n&~mask) | (m&mask)
            except StopIteration:
                self.play_stop()

        if self.recordfile is not None:
            self.recordfile.write(n.hex + b'\n')

        if self.globalrecfile is not None:
            self.globalrecfile.write(n.hex + b'\n')

        return n

macro_funcs = {}

def macro(f):
    macro_funcs[f.__name__] = f
    return f

@macro
def mash(divider):
    divider = int(divider, 10)
    s = State(buttons=0)
    while True:
        for i in range(divider+1):
            yield s
        s.buttons = ~s.buttons & 0xff

@macro
def file(filename):
    try:
        with open(filename, 'rb') as replay:
            for line in replay:
                yield State.fromhex(line)
    except FileNotFoundError:
        logger.error('Macro file "{:s}" does not exist yet.'.format(filename))
        raise StopIteration

@macro
def fileloop(filename):
    try:
        while True:
            with open(filename, 'rb') as replay:
                for line in replay:
                    yield State.fromhex(line)
    except FileNotFoundError:
        logger.error('Macro file "{:s}" does not exist yet.'.format(filename))
        raise StopIteration