import sdl2
import sdl2.ext


class Window(object):
    def __init__(self):
        sdl2.ext.init()
        self.window = sdl2.ext.Window('Switch Controller', size=(320, 240))
        self.window.show()

class WindowClosed(Exception):
    pass