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


import logging
import os
import subprocess

logger = logging.getLogger(__name__)

from .configfs import Directory, NotExist


class Gadget(object):
    CONFIGDIR = '/sys/kernel/config/usb_gadget/'

    def __init__(self, name, udc, device_params, device_strings, make_function):
        self._name = name
        self._udc = udc
        self._device_params = device_params
        self._device_strings = device_strings
        self._make_function = make_function
        self._function = None

        self._configfs = Directory(Gadget.CONFIGDIR)[self._name]

    @property
    def mount_point(self):
        return '/dev/ffs-' + self._name

    @property
    def function(self):
        return self._function

    def __enter__(self):
        logger.debug('Creating gadget')

        for k, v in self._device_params.items():
            setattr(self._configfs, k, v)

        for k, v in self._device_strings.items():
            setattr(self._configfs.strings['0x409'], k, v)

        self._configfs.configs['c.1'].MaxPower = '250'

        self.add_function_to_config('ffs.' + self._name, 'c.1')

        os.makedirs(self.mount_point, exist_ok=True)
        subprocess.call(['mount', '-c', '-t', 'functionfs', self._name, self.mount_point])

        self._function = self._make_function(self)

        self.bind()

        return self

    def __exit__(self, *args):
        logger.info('Tearing down gadget')

        self.unbind()

        if self._function is not None:
            self._function.close()

        if subprocess.call(['umount', self.mount_point]):
            logger.info("Can't teardown gadget because functionfs is still in use.")
            return

        self.remove_function_from_config('ffs.' + self._name, 'c.1')
        del self._configfs.functions['ffs.' + self._name]
        del self._configfs.configs['c.1']
        del self._configfs.strings['0x409']

        self.remove_gadget()

    def add_function_to_config(self, function, config):
        if type(self._configfs.functions[function]) == NotExist:
            self._configfs.functions[function] = None
        self._configfs.configs[config][function] = self._configfs.functions[function]

    def remove_function_from_config(self, function, config):
        del self._configfs.configs[config][function]

    def bind(self):
        logger.info('Binding to {}'.format(self._udc))
        self._configfs.UDC = self._udc

    def unbind(self):
        self._configfs.UDC = ''

    def remove_gadget(self):
        del Directory(Gadget.CONFIGDIR)[self._name]
