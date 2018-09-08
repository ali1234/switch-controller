import logging

from .state import State

logger = logging.getLogger(__name__)

class MacroManager(object):
    def __init__(self, states, macrosfilename=None):
        self.states = states
        self.macros = {}

        self.recordmacro = None
        self.recordfile = None

        self.playmacro = None
        self.playfile = None

        if macrosfilename is not None:
            with open(macrosfilename) as f:
                for line in f:
                    line = line.strip().split()
                    if len(line) == 2:
                        self.macros[line[0]] = (line[1], State.all())
                    if len(line) == 3:
                        self.macros[line[0]] = (line[1], State.fromhex(line[2]))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.record_stop()
        self.play_stop()

    def record_start(self, macro):
        if self.recordfile is None:
            if self.playmacro == macro:
                self.play_stop()
            self.recordmacro = macro
            self.recordfile = open(self.macros[macro][0], 'wb')
            logger.info('Recording to macro "{:s}" (file "{:s}")'.format(self.recordmacro, self.macros[self.recordmacro][0]))
        elif self.recordmacro == macro:
            self.record_stop()
        else:
            logger.error('Already recording a macro.')

    def record_stop(self):
        if self.recordfile is not None:
            self.recordfile.close()
            self.recordfile = None
            logger.info('Stopped recording to macro "{:s}" (file "{:s}")'.format(self.recordmacro, self.macros[self.recordmacro][0]))
            self.recordmacro = None

    def play_start(self, macro):
        if self.recordmacro == macro:
            self.record_stop()
            return
        if self.playfile is not None:
            self.play_stop()
        self.playmacro = macro
        self.playfile = open(self.macros[macro][0], 'rb')
        logger.info('Playing macro "{:s}" (file "{:s}")'.format(self.playmacro, self.macros[self.playmacro][0]))

    def play_stop(self):
        if self.playfile is not None:
            self.playfile.close()
            self.playfile = None
            logger.info('Stopped playing macro "{:s}" (file "{:s}")'.format(self.playmacro, self.macros[self.playmacro][0]))
            self.playmacro = None

    def key_pressed(self, k):
        if len(k) != 1:
            return
        if k in self.macros:
            self.play_start(k)
        elif k.lower() in self.macros:
            self.record_start(k.lower())

    def __iter__(self):
        return self

    def __next__(self):
        n = next(self.states)
        if self.playfile is not None:
            try:
                m = State.fromhex(next(self.playfile))
                mask = self.macros[self.playmacro][1]
                n = (n&~mask) | (m&mask)
            except StopIteration:
                self.play_stop()

        if self.recordfile is not None:
            self.recordfile.write(n.hex + b'\n')

        return n