import logging

import sdl2
import sdl2.ext

from .state import State

logger = logging.getLogger(__name__)


class Window(object):



    def __init__(self, div=2, padding=6):

        self.div = div
        size = 256 >> div
        width = (3 * size) + (4 * padding)
        height = size + (2 * padding)

        # calculate coordinates and save them for drawing later
        self.lstick = (padding, padding, size, size)
        self.rstick = ((2 * padding) + size, padding, size, size)
        self.dstick = ((3 * padding) + (2*size), padding, size, size)
        self.centrelines = [
            (self.lstick[0] + (size >> 1), self.lstick[1], self.lstick[0] + (size >> 1), self.lstick[1] + size - 1),
            (self.lstick[0], self.lstick[1] + (size >> 1), self.lstick[0] + size - 1, self.lstick[1] + (size >> 1)),
            (self.rstick[0] + (size >> 1), self.rstick[1], self.rstick[0] + (size >> 1), self.rstick[1] + size - 1),
            (self.rstick[0], self.rstick[1] + (size >> 1), self.rstick[0] + size - 1, self.rstick[1] + (size >> 1)),
            (self.dstick[0] + (size >> 1), self.dstick[1], self.dstick[0] + (size >> 1), self.dstick[1] + size - 1),
            (self.dstick[0], self.dstick[1] + (size >> 1), self.dstick[0] + size - 1, self.dstick[1] + (size >> 1)),
        ]

        self.buttons = [(padding + (n * (padding + (32>>div))), height, 32>>div, 32>>div) for n in range(14)]

        height += padding + (32>>div)

        sdl2.ext.init()

        self.window = sdl2.ext.Window('Switch Controller', size=(width, height))
        self.window.show()
        self.renderer = sdl2.ext.Renderer(self.window)

        self.prev_state = State()

    def update(self, state):
        """Draw the supplied controller state in the SDL window."""
        if state != self.prev_state:
            self.renderer.clear((255, 255, 255))
            for p in self.centrelines:
                self.renderer.draw_line(p, (200, 200, 200))
            self.renderer.draw_rect([self.lstick, self.rstick, self.dstick], (0, 0, 0))
            self.renderer.fill([
                (self.lstick[0] + (state.lx>>self.div) - 4, self.lstick[1] + (state.ly>>self.div) - 4, 9, 9),
                (self.rstick[0] + (state.rx>>self.div) - 4, self.rstick[1] + (state.ry>>self.div) - 4, 9, 9),
            ], (255, 0, 0))

            self.renderer.draw_rect(self.buttons, (0, 0, 0))
            for n,b in enumerate(self.buttons):
                if state.buttons&(1<<n):
                    self.renderer.fill((b[0]+1, b[1]+1, b[2]-2, b[3]-2), (255, 0, 0))

            hatx, haty = 128, 128

            if state.hat == 0:
                hatx, haty = 128, 0
            if state.hat == 1:
                hatx, haty = 255, 0
            if state.hat == 2:
                hatx, haty = 255, 128
            if state.hat == 3:
                hatx, haty = 255, 255
            if state.hat == 4:
                hatx, haty = 128, 255
            if state.hat == 5:
                hatx, haty = 0, 255
            if state.hat == 6:
                hatx, haty = 0, 128
            if state.hat == 7:
                hatx, haty = 0, 0

            self.renderer.fill((self.dstick[0] + (hatx>>self.div) - 4, self.dstick[1] + (haty>>self.div) - 4, 9, 9), (255, 0, 0))

            self.renderer.present()

            self.prev_state = state


class WindowClosed(Exception):
    pass