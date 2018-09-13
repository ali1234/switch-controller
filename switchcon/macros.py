# This file is part of switchcon
# Copyright (C) 2018  Alistair Buxton <a.j.buxton@gmail.com>
#
# switchcon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# switchcon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with switchcon.  If not, see <http://www.gnu.org/licenses/>.

import logging
import pathlib

from .state import State

logger = logging.getLogger(__name__)

class MacroManager(object):
    def __init__(self, states, macros_dir='.'):
        self.states = states

        self.recordmacro = None
        self.recordfile = None

        self.playmacro = None
        self.playiter = None

        self.macros_dir = pathlib.Path(macros_dir)
        if not self.macros_dir.is_dir():
            raise NotADirectoryError("Macro dir doesn't exist or is not a directory.")

        self.previous_state = State()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.record_stop()
        self.play_stop()

    def log_macro_event(self, event, macro):
        logger.info('{:s} macro {:s}'.format(
                event, macro.name
        ))

    def record_start(self, macro):
        if self.recordfile is None:
            if self.playmacro == macro:
                self.play_stop()
            self.recordmacro = macro
            self.recordfile = macro.open('wb')
            self.log_macro_event('Recording to', macro)
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
        self.playiter = file(macro)
        self.log_macro_event('Playing', self.playmacro)

    def play_stop(self):
        if self.playiter is not None:
            self.playiter.close()
            self.playiter = None
            self.log_macro_event('Stopped playing', self.playmacro)
            self.playmacro = None

    def key_pressed(self, k):

        if self.recordmacro:
            self.record_stop()
        else:
            macro_name = self.previous_state.hexstr[:6] + '.macro'
            macro_file = self.macros_dir / macro_name

            if not macro_file.exists():
                self.record_start(macro_file)
            elif macro_file.is_file():
                self.play_start(macro_file)
            else:
                raise FileNotFoundError("Macro file exists but isn't a regular file.")

    def __iter__(self):
        return self

    def __next__(self):
        n = next(self.states)
        self.previous_state = n
        if self.playiter is not None:
            try:
                m = next(self.playiter)
                # OR buttons
                n |= (m&State(0x00, 0xffff, 0, 0, 0, 0))
                # user hat overrides macro hat if not centred
                n.hat = m.hat if n.hat == 8 else n.hat
                # user axes override macro axes if > 50%
                n.axes = [na if (na < 64) or (na > 192) else ma for na, ma in zip(n.axes, m.axes)]
            except StopIteration:
                self.play_stop()

        if self.recordfile is not None:
            self.recordfile.write(n.hex + b'\n')

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