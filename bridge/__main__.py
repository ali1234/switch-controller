#!/usr/bin/env python3


import argparse
import fcntl
import itertools
import logging
import os
import sys
import termios

import sdl2
import sdl2.ext
import serial

from tqdm import tqdm

from .controller import Controller
from .state import State
from .macros import MacroManager

class Handler(logging.Handler):
    def emit(self, record):
        tqdm.write(self.format(record))

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = [Handler()]
logger = logging.getLogger(__name__)


class NonBlockingInput(object):

    def __enter__(self):
        self.old = termios.tcgetattr(sys.stdin)
        new = termios.tcgetattr(sys.stdin)
        new[3] = new[3] & ~(termios.ICANON | termios.ECHO)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new)

        # set for non-blocking io
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

    def __exit__(self, *args):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old)


def replay_states(filename):
    with open(filename, 'rb') as replay:
        for line in replay:
            yield State.fromhex(line)


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
    parser.add_argument('-M', '--load-macros', type=str, default=None, help='Load in-line macro definition file. Default: None')
    parser.add_argument('-D', '--log-level', type=str, default='INFO', help='Debugging level. CRITICAL, ERROR, WARNING, INFO, DEBUG. Default=INFO')

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)
    logging.basicConfig(level=numeric_level)

    if args.list_controllers:
        Controller.enumerate()
        exit(0)

    states = []

    if args.playback is None or args.dontexit:
        states = Controller(args.controller)
    if args.playback is not None:
        states = itertools.chain(replay_states(args.playback), states)

    ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None)
    logger.info('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

    with NonBlockingInput():
        with MacroManager(states, macrosfilename=args.load_macros, globalrecfilename=args.record) as mm:
            with tqdm(unit=' updates', disable=args.quiet, dynamic_ncols=True) as pbar:

                try:

                    while True:

                        for event in sdl2.ext.get_events():
                            # we have to fetch the events from SDL in order for the controller
                            # state to be updated.
                            pass

                        mm.key_pressed(sys.stdin.read(1))

                        try:
                            message = next(mm).hex
                            ser.write(message + b'\n')
                            pbar.set_description('Sent {:s}'.format(message.decode('utf8')))
                            pbar.update()
                        except StopIteration:
                            break

                        while True:
                            # wait for the arduino to request another state.
                            response = ser.read(1)
                            if response == b'U':
                                break
                            elif response == b'X':
                                print('Arduino reported buffer overrun.')

                except KeyboardInterrupt:
                    logger.critical('\nExiting due to keyboard interrupt.')


if __name__ == '__main__':
    main()