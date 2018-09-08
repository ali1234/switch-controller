#!/usr/bin/env python3


import argparse
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
    try:
        with open(filename, 'rb') as replay:
            yield from replay.readlines()
    except FileNotFoundError:
        print("Warning: replay file not found: {:s}".format(filename))

def example_macro():
    buttons = 0
    hat = 8
    rx = 128
    ry = 128
    for i in range(240):
        lx = int((1.0 + math.sin(2 * math.pi * i / 240)) * 127)
        ly = int((1.0 + math.cos(2 * math.pi * i / 240)) * 127)
        rawbytes = struct.pack('>BHBBBB', hat, buttons, lx, ly, rx, ry)
        yield binascii.hexlify(rawbytes) + b'\n'


class InputStack(object):
    def __init__(self, recordfilename=None):
        self.l = []
        self.recordfilename = recordfilename
        self.recordfile = None
        self.macrofile = None

    def __enter__(self):
        if self.recordfilename is not None:
            self.recordfile = open(self.recordfilename, 'wb')
        return self

    def __exit__(self, *args):
        if self.recordfile is not None:
            self.recordfile.close()
        self.macro_end()

    def macro_start(self, filename):
        if self.macrofile is None:
            self.macrofile = open(filename, 'wb')
        else:
            print('ERROR: Already recording a macro.')

    def macro_end(self):
        if self.macrofile is not None:
            self.macrofile.close()
            self.macrofile = None

    def push(self, it):
        self.l.append(it)

    def pop(self):
        self.l.pop()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            try:
                message = next(self.l[-1])
                if self.recordfile is not None:
                    self.recordfile.write(message)
                if self.macrofile is not None:
                    self.macrofile.write(message)
                return message
            except StopIteration:
                self.l.pop()
            except IndexError:
                raise StopIteration


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

    with KeyboardContext() as kb:

        ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None)
        print('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

        with InputStack(args.record) as input_stack:

            if args.playback is None or args.dontexit:
                live = Controller(args.controller)
                input_stack.push(live)
            if args.playback is not None:
                input_stack.push(replay_states(args.playback))

            with tqdm(unit=' updates', disable=args.quiet) as pbar:
                try:

                    while True:

                        for event in sdl2.ext.get_events():
                            # we have to fetch the events from SDL in order for the controller
                            # state to be updated.

                            # example of running a macro when a joystick button is pressed:
                            #if event.type == sdl2.SDL_JOYBUTTONDOWN:
                            #    if event.jbutton.button == 1:
                            #        input_stack.push(example_macro())
                            # or play from file:
                            #        input_stack.push(replay_states(filename))

                            pass

                        try:
                            c = chr(kb.getch())
                            if c in macros:
                                input_stack.push(replay_states(macros[c]))
                            elif c.lower() in macros:
                                input_stack.macro_start(macros[c.lower()])
                            elif c == ' ':
                                input_stack.macro_end()
                        except ValueError:
                            pass

                        try:
                            message = next(input_stack)
                            ser.write(message)
                        except StopIteration:
                            break

                        # update speed meter on console.
                        pbar.set_description('Sent {:s}'.format(message[:-1].decode('utf8')))
                        pbar.update()

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