import logging

import sdl2

from .state import State

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

        # Mapping for X-box S Controller
        sdl2.SDL_GameControllerAddMapping(
            b"030000005e0400008902000021010000,Classic XBOX Controller,"
            b"a:b0,b:b1,y:b4,x:b3,start:b7,guide:,back:b6,leftstick:b8,"
            b"rightstick:b9,dpup:h0.1,dpleft:h0.8,dpdown:h0.4,dpright:h0.2,"
            b"leftx:a0,lefty:a1,rightx:a3,righty:a4,lefttrigger:a2,"
            b"righttrigger:a5,leftshoulder:b5,rightshoulder:b2,"
        )

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

        self.previous_state = State()

    def __iter__(self):
        return self

    def __next__(self):
        buttons = sum([sdl2.SDL_GameControllerGetButton(self.controller, b) << n for n, b in enumerate(Controller.buttonmapping)])
        buttons |= (abs(sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)) > self.trigger_deadzone) << 6
        buttons |= (abs(sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)) > self.trigger_deadzone) << 7

        hat = Controller.hatcodes[sum([sdl2.SDL_GameControllerGetButton(self.controller, b) << n for n, b in enumerate(Controller.hatmapping)])]

        rawaxis = [sdl2.SDL_GameControllerGetAxis(self.controller, n) for n in Controller.axismapping]
        axis = [((0 if abs(x) < self.axis_deadzone else x) >> 8) + 128 for x in rawaxis]

        state = State(hat, buttons, *axis)
        # TODO: quantize
        self.previous_state = state
        return state

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