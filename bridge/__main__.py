#!/usr/bin/env python3


import argparse
import itertools
from contextlib import contextmanager

import sdl2
import sdl2.ext
import struct
import binascii
import serial
import math
import time

from tqdm import tqdm

curses_available = False

try:
    import curses
    curses_available = True
except ImportError:
    pass


from .controller import Controller
from .state import State
from .macros import MacroManager

class KeyboardContext(object):
    def __enter__(self):
        if curses_available:
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)
            self.stdscr.nodelay(True)
        return self

    def __exit__(self, *args):
        if curses_available:
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.echo()
            curses.endwin()

    def getch(self):
        if curses_available:
            return self.stdscr.getch()
        else:
            return curses.ERR


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

    args = parser.parse_args()

    if args.list_controllers:
        Controller.enumerate()
        exit(0)

    macros = {}

    if args.load_macros is not None:
        with open(args.load_macros) as f:
            for line in f:
                line = line.strip().split(maxsplit=2)
                if len(line) == 2:
                    macros[line[0]] = line[1]

    states = []

    if args.playback is None or args.dontexit:
        states = Controller(args.controller)
    if args.playback is not None:
        states = itertools.chain(replay_states(args.playback), states)

    ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None)
    print('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

    with KeyboardContext() as kb:
        with MacroManager(states, macrosfilename=args.load_macros) as mm:
            with tqdm(unit=' updates', disable=args.quiet) as pbar:

                try:

                    while True:

                        for event in sdl2.ext.get_events():
                            # we have to fetch the events from SDL in order for the controller
                            # state to be updated.
                            pass

                        try:
                            mm.key_pressed(chr(kb.getch()))
                        except ValueError:
                            pass

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
                    print('\nExiting due to keyboard interrupt.')

if __name__ == '__main__':
    main()