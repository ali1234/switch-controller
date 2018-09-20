import itertools

from .state import State

macros_dict = {}

def macro(f):
    macros_dict[f.__name__] = f
    return f


def mash(divider):
    divider = int(divider, 10)
    s = State(buttons=0)
    while True:
        for i in range(divider+1):
            yield s
        s.buttons = ~s.buttons & 0xff


def press_and_release(button, n, state=None):
    # if a state argument is passed in we will modify it - so other inputs will be kept
    # if not make a new one, all other buttons and axes will be at rest
    if state is None:
        state = State()

    setattr(state, button, 1)
    for x in range(n):
        yield state
    setattr(state, button, 0)
    for x in range(n):
        yield state


# this is your "main" function - select it with the "-c fake" controller input
def fakeinput():
    state = State()

    for i in range(10):
        for button in [
            'y', 'b', 'a', 'x', 'l', 'r', 'zl', 'zr',
            'select', 'start', 'lclick', 'rclick', 'home', 'capture'
        ]:
            yield from press_and_release(button, 6, state)

    for i in itertools.count():
        state.buttons = i&0xffff
        for i in range(6):
            yield state


@macro
def testmacro():
    for i in range(10):
        yield from press_and_release('a', 100)