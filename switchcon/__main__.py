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


import argparse
import itertools
import logging

import sdl2
import sdl2.ext

from tqdm import tqdm

from .controller import Controller
from .state import State
from .macros import MacroManager
from .window import Window, WindowClosed
from .hal import HAL
from .fakeinput import fakeinput

class Handler(logging.Handler):
    def emit(self, record):
        tqdm.write(self.format(record))

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = [Handler()]
logger = logging.getLogger(__name__)


def replay_states(filename):
    with open(filename, 'rb') as replay:
        for line in replay:
            yield State.fromhex(line)


class Recorder(object):
    def __init__(self, filename):
        self.filename = filename
        self.file = None

    def __enter__(self):
        if self.filename is not None:
            self.file = open(self.filename, 'wb')
        return self

    def __exit__(self, *args):
        if self.file is not None:
            self.file.close()

    def write(self, state):
        if self.file is not None:
            self.file.write(state.hex + b'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list-controllers', action='store_true', help='Display a list of controllers attached to the system.')
    parser.add_argument('-c', '--controller', type=str, default='0', help='Controller to use. Default: 0.')
    parser.add_argument('-m', '--macro-controller', metavar='CONTROLLER:RECORD_BUTTON:PLAY_BUTTON', type=str, default=None, help='Controller and buttons to use for macro control. Default: None.')
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyUSB0', help='Serial port or "functionfs" for direct USB mode. Default: /dev/ttyUSB0.')
    parser.add_argument('-b', '--baud-rate', type=int, default=115200, help='Baud rate. Default: 115200.')
    parser.add_argument('-u', '--udc', type=str, default='dummy_udc.0', help='UDC for direct USB mode. Default: dummy_udc.0 (loopback mode).')
    parser.add_argument('-R', '--record', type=str, default=None, help='Record events to file.')
    parser.add_argument('-P', '--playback', type=str, default=None, help='Play back events from file.')
    parser.add_argument('-d', '--dontexit', action='store_true', help='Switch to live input when playback finishes, instead of exiting. Default: False.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Disable speed meter. Default: False.')
    parser.add_argument('-M', '--macros-dir', type=str, default='.', help='Directory to save macros. Default: current directory.')
    parser.add_argument('-D', '--log-level', type=str, default='INFO', help='Debugging level. CRITICAL, ERROR, WARNING, INFO, DEBUG. Default=INFO')

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)
    root_logger.setLevel(numeric_level)

    if args.list_controllers:
        Controller.enumerate()
        exit(0)

    states = []

    if args.playback is None or args.dontexit:
        if args.controller == 'fake':
            states = fakeinput()
        else:
            states = Controller(args.controller)
    if args.playback is not None:
        states = itertools.chain(replay_states(args.playback), states)

    macro_controller = None
    macro_record = None
    macro_play = None

    if args.macro_controller is not None:
        try:
            macro_controller, macro_record, macro_play = args.macro_controller.rsplit(':', maxsplit=3)
            macro_record = int(macro_record, 10)
            macro_play = int(macro_play, 10)
        except ValueError:
            logger.critical('Macro controller must be <controller number or name>:<record button>:<play button>')
            exit(-1)

        try:
            n = int(macro_controller, 10)
            if n < sdl2.SDL_NumJoysticks():
                sdl2.SDL_JoystickOpen(n)
                macro_controller = n
        except ValueError:
            for n in range(sdl2.SDL_NumJoysticks()):
                name = sdl2.SDL_JoystickNameForIndex(n)
                if name is not None:
                    name = name.decode('utf8')
                    if name == macro_controller:
                        sdl2.SDL_JoystickOpen(n)
                        macro_controller = n

    window = None
    try:
        window = Window()
    except sdl2.ext.common.SDLError:
        logger.warning('Could not create a window with SDL. Keyboard input will not be available.')
        pass


    with MacroManager(states, macros_dir=args.macros_dir) as mm:
        with Recorder(args.record) as record:
            with HAL(args.port, args.baud_rate, args.udc) as hal:
                with tqdm(unit=' updates', disable=args.quiet, dynamic_ncols=True) as pbar:

                    try:

                        while True:

                            for event in sdl2.ext.get_events():
                                # we have to fetch the events from SDL in order for the controller
                                # state to be updated.
                                if event.type == sdl2.SDL_WINDOWEVENT:
                                    if event.window.event == sdl2.SDL_WINDOWEVENT_CLOSE:
                                        raise WindowClosed
                                else:
                                    if event.type == sdl2.SDL_KEYDOWN and event.key.repeat == 0:
                                        logger.debug('Key down: {:s}'.format(sdl2.SDL_GetKeyName(event.key.keysym.sym).decode('utf8')))
                                        if event.key.keysym.sym == sdl2.SDLK_SPACE:
                                            mm.key_pressed(record=True)
                                        elif event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
                                            mm.key_pressed(record=False)
                                    elif event.type == sdl2.SDL_KEYUP:
                                        logger.debug('Key up: {:s}'.format(sdl2.SDL_GetKeyName(event.key.keysym.sym).decode('utf8')))
                                    elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                                        if event.jdevice.which == macro_controller:
                                            logger.debug('Macro controller: {:d}'.format(event.jbutton.button))
                                            if event.jbutton.button == macro_record:
                                                mm.key_pressed(record=True)
                                            elif event.jbutton.button == macro_play:
                                                mm.key_pressed(record=False)

                            # wait for the arduino to request another state.
                            if hal.poll():
                                state = next(mm)
                                hal.write(state)
                                record.write(state)
                                pbar.set_description('Sent {:s}'.format(state.hexstr))
                                pbar.update()
                                if window is not None:
                                    window.update(state)

                    except StopIteration:
                        logger.info('Exiting because replay finished.')
                    except KeyboardInterrupt:
                        logger.info('Exiting due to keyboard interrupt.')
                    except WindowClosed:
                        logger.info('Exiting because input window was closed.')


if __name__ == '__main__':
    main()