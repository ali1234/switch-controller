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

import sdl2

from .state import State

logger = logging.getLogger(__name__)

class MacroManager(object):
    def __init__(self, states, macros_dir='.', record_button=0, play_button=1, function_macros={}):
        self.states = states

        self.recordmacro = None
        self.recordfile = None

        self.playmacro = None
        self.playiter = None

        self.fmacro = None
        self.fiter = None

        self.record_button = record_button
        self.play_button = play_button

        self.macros_dir = pathlib.Path(macros_dir)
        if not self.macros_dir.is_dir():
            raise NotADirectoryError("Macro dir doesn't exist or is not a directory.")

        self.function_macros = function_macros

        self.previous_state = State()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.record_stop()
        self.play_stop()

    def log_macro_event(self, event, macro):
        name = str(macro)
        try:
            name = macro.name
        except AttributeError:
            pass
        logger.info('{:s} macro {:s}'.format(
                event, name
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
            try:
                self.playiter.close()
            except AttributeError:
                pass
            self.playiter = None
            self.log_macro_event('Stopped playing', self.playmacro)
            self.playmacro = None

    def key_event(self, key, down):
        if key >= sdl2.SDLK_0 and key <= sdl2.SDLK_9:
            button = key - sdl2.SDLK_0
            logger.debug('Passing key to button {:d}'.format(button))
            self.button_event(button, down)

        if down:
            if key == sdl2.SDLK_SPACE:
                self.recorder_control(True)
            elif key == sdl2.SDLK_KP_ENTER:
                self.recorder_control(False)



    def button_event(self, button, down):
        if down:
            if button == self.record_button:
                self.recorder_control(True)
            elif button == self.play_button:
                self.recorder_control(False)
            else:
                if button in self.function_macros:
                    if self.playmacro is None:
                        self.playmacro = self.function_macros[button].__name__
                        self.log_macro_event('Playing', self.playmacro)
                        self.playiter = self.function_macros[button]()
                    else:
                        self.play_stop()

        else:
            pass

    def recorder_control(self, record):

        if self.recordmacro:
            self.record_stop()
        else:
            macro_name = self.previous_state.hexstr[:6] + '.macro'
            macro_file = self.macros_dir / macro_name

            if record:
                self.record_start(macro_file)
            else:
                if not macro_file.exists():
                    logger.error('Macro not recorded yet.')
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
                n |= (m&State(0xffff, 0x00, 0, 0, 0, 0))
                # user hat overrides macro hat if not centred
                n.hat = m.hat if n.hat == 8 else n.hat
                # user axes override macro axes if > 50%
                n.axes = [na if (na < 64) or (na > 192) else ma for na, ma in zip(n.axes, m.axes)]
            except StopIteration:
                self.play_stop()

        if self.recordfile is not None:
            self.recordfile.write(n.hex + b'\n')

        return n


def file(filename):
    try:
        with open(filename, 'rb') as replay:
            for line in replay:
                yield State.fromhex(line)
    except FileNotFoundError:
        logger.error('Macro file "{:s}" does not exist yet.'.format(filename))
        raise StopIteration


def fileloop(filename):
    try:
        while True:
            with open(filename, 'rb') as replay:
                for line in replay:
                    yield State.fromhex(line)
    except FileNotFoundError:
        logger.error('Macro file "{:s}" does not exist yet.'.format(filename))
        raise StopIteration