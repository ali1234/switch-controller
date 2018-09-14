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


import binascii
import logging

import serial

from .functionfs import Gadget, HIDFunction
from .gadgetfs import Gadget as GadgetFS

logger = logging.getLogger(__name__)

class Serial(object):

    def __init__(self, port='/dev/ttyUSB0', baud_rate=115200):
        self._port = port
        self._baud_rate = baud_rate
        self._file = None
        self._state = True

    def __enter__(self):
        self._file = serial.Serial(
            self._port, self._baud_rate,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE, timeout=0.1
        )
        logger.info('Using {:s} at {:d} baud for comms.'.format(self._port, self._baud_rate))
        return self

    def __exit__(self, *args):
        self._file.close()

    def poll(self):
        response = self._file.read(1)
        if response == b'U':
            return True
        elif response == b'X':
            logger.error('Arduino reported buffer overrun.')
        else:
            if self._state:
                logger.warning('Serial read timed out.')
                self._state = False
        return False

    def write(self, state):
        self._file.write(state.hex + b'\n')


class GadgetWrapper(object):
    def __init__(self, gadget):
        self._gadget = gadget

    def __enter__(self):
        self._gadget.__enter__()
        return self

    def __exit__(self, *args):
        self._gadget.__exit__(*args)

    def poll(self):
        self._gadget.processEvents()
        return self._gadget._report_requested

    def write(self, state):
        # this write blocks so we get sync for free
        self._gadget._ep_list[1].write(state.bytes)



def HAL(port, baud_rate, udc):

    device_params = {
        'idVendor': '0x0f0d',
        'idProduct': '0x00c1',
        'bcdUSB': '0x0200',
        'bcdDevice': '0x0572',
        'bDeviceClass': '0x0',
        'bDeviceSubClass': '0x0',
        'bDeviceProtocol': '0x0',
    }

    device_strings = {
        'manufacturer': 'HORI CO.,LTD.',
        'product': 'HORIPAD S',
    }

    report_desc = binascii.unhexlify(
        "05010905A10115002501350045017501"
        "950E05091901290E8102950281010501"
        "2507463B017504950165140939814265"
        "009501810126FF0046FF000930093109"
        "320935750895048102750895018101C0"
    )

    if port == 'functionfs':
        return GadgetWrapper(Gadget('switchcon', udc, device_params, device_strings, lambda g: HIDFunction(g, report_desc)))

    elif port == 'gadgetfs':
        if udc == 'dummy_udc.0':
            udc = 'dummy_udc'
        return GadgetWrapper(GadgetFS(udc, device_params, device_strings, report_desc))

    else:
        return Serial(port, baud_rate)