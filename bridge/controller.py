import binascii
import logging
import struct

import sdl2

logger = logging.getLogger(__name__)

class Controller(object):

    buttonmapping = [
        sdl2.SDL_CONTROLLER_BUTTON_X,  # Y
        sdl2.SDL_CONTROLLER_BUTTON_A,  # B
        sdl2.SDL_CONTROLLER_BUTTON_B,  # A
        sdl2.SDL_CONTROLLER_BUTTON_Y,  # X
        sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,  # L
        sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,  # R
        sdl2.SDL_CONTROLLER_BUTTON_INVALID,  # ZL
        sdl2.SDL_CONTROLLER_BUTTON_INVALID,  # ZR
        sdl2.SDL_CONTROLLER_BUTTON_BACK,  # SELECT
        sdl2.SDL_CONTROLLER_BUTTON_START,  # START
        sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,  # LCLICK
        sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,  # RCLICK
        sdl2.SDL_CONTROLLER_BUTTON_GUIDE,  # HOME
        sdl2.SDL_CONTROLLER_BUTTON_INVALID,  # CAPTURE
    ]

    axismapping = [
        sdl2.SDL_CONTROLLER_AXIS_LEFTX,  # LX
        sdl2.SDL_CONTROLLER_AXIS_LEFTY,  # LY
        sdl2.SDL_CONTROLLER_AXIS_RIGHTX,  # RX
        sdl2.SDL_CONTROLLER_AXIS_RIGHTY,  # RY
    ]

    hatmapping = [
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,  # UP
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,  # RIGHT
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,  # DOWN
        sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,  # LEFT
    ]

    hatcodes = [8, 0, 2, 1, 4, 8, 3, 8, 6, 7, 8, 8, 5, 8, 8]

    def __init__(self, controller_id, axis_deadzone=10000, trigger_deadzone=0):

        sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER)

        self.controller = None
        self.name = 'controller {:s}'.format(controller_id)

        try:
            n = int(controller_id, 10)
            if n < sdl2.SDL_NumJoysticks():
                self.controller = sdl2.SDL_GameControllerOpen(n)
        except ValueError:
            for n in range(sdl2.SDL_NumJoysticks()):
                name = sdl2.SDL_JoystickNameForIndex(n)
                if name is not None:
                    name = name.decode('utf8')
                    if name == controller_id:
                        self.controller = sdl2.SDL_GameControllerOpen(n)

        if self.controller is None:
            raise Exception('Controller not found: {:s}'.format(controller_id))

        try:
            self.name = sdl2.SDL_JoystickName(sdl2.SDL_GameControllerGetJoystick(self.controller)).decode('utf8')
        except AttributeError:
            pass

        logger.info('Using {:s} for input.'.format(self.name))

        self.axis_deadzone = axis_deadzone
        self.trigger_deadzone = trigger_deadzone

    def __iter__(self):
        return self

    def __next__(self):
        buttons = sum([sdl2.SDL_GameControllerGetButton(self.controller, b) << n for n, b in enumerate(Controller.buttonmapping)])
        buttons |= (abs(sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)) > self.trigger_deadzone) << 6
        buttons |= (abs(sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)) > self.trigger_deadzone) << 7

        hat = Controller.hatcodes[sum([sdl2.SDL_GameControllerGetButton(self.controller, b) << n for n, b in enumerate(Controller.hatmapping)])]

        rawaxis = [sdl2.SDL_GameControllerGetAxis(self.controller, n) for n in Controller.axismapping]
        axis = [((0 if abs(x) < self.axis_deadzone else x) >> 8) + 128 for x in rawaxis]

        rawbytes = struct.pack('>BHBBBB', hat, buttons, *axis)
        return binascii.hexlify(rawbytes) + b'\n'

    @staticmethod
    def enumerate():
        sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER)

        print('Controllers connected to this system:')
        for n in range(sdl2.SDL_NumJoysticks()):
            name = sdl2.SDL_JoystickNameForIndex(n)
            if name is not None:
                name = name.decode('utf8')
            print(n, ':', name)
        print('Note: These are numbered by connection order. Numbers will change if you unplug a controller.')