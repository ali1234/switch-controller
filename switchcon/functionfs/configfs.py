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


import os, stat

import logging

logger = logging.getLogger(__name__)


class Directory(object):
    def __init__(self, path):
        object.__setattr__(self, 'path', path)

    def __setattr__(self, key, value):
        path = object.__getattribute__(self, 'path')
        if type(value) == str:
            with open(os.path.join(path, key), 'w') as k:
                k.write(value)
        elif type(value) == bytes:
            with open(os.path.join(path, key), 'wb') as k:
                k.write(value)

        elif type(value) == Directory:
            try:
                os.symlink(object.__getattribute__(value, 'path'), os.path.join(path, key))
            except FileExistsError:
                os.unlink(os.path.join(path, key))
                os.symlink(object.__getattribute__(value, 'path'), os.path.join(path, key))
        elif value is None:
            os.makedirs(os.path.join(path, key))

    def __getattribute__(self, key):
        path = object.__getattribute__(self, 'path')
        attr = os.path.join(path, key)
        try:
            mode = os.stat(attr)[stat.ST_MODE]
            if stat.S_ISDIR(mode):
                return Directory(attr)
            elif stat.S_ISREG(mode):
                with open(attr, 'r') as f:
                    value = f.read()
                return value
        except FileNotFoundError:
            return NotExist(attr)

    def __delattr__(self, key):
        path = object.__getattribute__(self, 'path')
        attr = os.path.join(path, key)
        mode = os.lstat(attr)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            os.rmdir(attr)
        else:
            os.unlink(attr)

    def __getitem__(self, key):
        return type(self).__getattribute__(self, key)

    def __setitem__(self, key, value):
        return type(self).__setattr__(self, key, value)

    def __delitem__(self, key):
        return type(self).__delattr__(self, key)


class NotExist(Directory):

    def __setattr__(self, key, value):
        path = object.__getattribute__(self, 'path')
        os.makedirs(path, exist_ok=True)
        Directory.__setattr__(self, key, value)
