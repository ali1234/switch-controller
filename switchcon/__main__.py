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
import serial

from tqdm import tqdm

from .controller import Controller
from .state import State
from .macros import MacroManager
from .window import Window, WindowClosed

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

    def write(self, data):
        if self.file is not None:
            self.file.write(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list-controllers', action='store_true', help='Display a list of controllers attached to the system.')
    parser.add_argument('-c', '--controller', type=str, default='0', help='Controller to use. Default: 0.')
    parser.add_argument('-b', '--baud-rate', type=int, default=115200, help='Baud rate. Default: 115200.')
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyUSB0', help='Serial port. Default: /dev/ttyUSB0.')
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
        states = Controller(args.controller)
    if args.playback is not None:
        states = itertools.chain(replay_states(args.playback), states)

    ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.1)
    logger.info('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

    window = None
    try:
        window = Window()
    except sdl2.ext.common.SDLError:
        logger.warning('Could not create a window with SDL. Keyboard input will not be available.')
        pass

    serial_state = True

    with MacroManager(states, macros_dir=args.macros_dir) as mm:
        with Recorder(args.record) as record:
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
                                    if  event.key.keysym.sym == sdl2.SDLK_SPACE:
                                        mm.key_pressed(True)
                                elif event.type == sdl2.SDL_KEYUP:
                                    logger.debug('Key up: {:s}'.format(sdl2.SDL_GetKeyName(event.key.keysym.sym).decode('utf8')))

                        # wait for the arduino to request another state.
                        response = ser.read(1)
                        if response == b'U':
                            state = next(mm)
                            ser.write(state.hex + b'\n')
                            record.write(state.hex + b'\n')
                            pbar.set_description('Sent {:s}'.format(state.hexstr))
                            pbar.update()
                            if window is not None:
                                window.update(state)
                            serial_state = True
                        elif response == b'X':
                            logger.error('Arduino reported buffer overrun.')
                        else:
                            if serial_state:
                                logger.warning('Serial read timed out.')
                                serial_state = False

                except StopIteration:
                    logger.info('Exiting because replay finished.')
                except KeyboardInterrupt:
                    logger.info('Exiting due to keyboard interrupt.')
                except WindowClosed:
                    logger.info('Exiting because input window was closed.')


if __name__ == '__main__':
    main()