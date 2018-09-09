import binascii
import struct


class Axis(object):
    """
    Descriptor class to proved named axes on top of the axes array.
    """
    def __init__(self, number):
        self.number = number

    def __get__(self, instance, owner):
        return instance._axes[self.number]

    def __set__(self, instance, value):
        instance._axes[self.number] = value


class State(object):
    """
    Class which holds a representation of a controller state and provides
    conversion to and from bytes and strings.
    """

    lx = Axis(0)
    ly = Axis(1)
    rx = Axis(2)
    ry = Axis(3)

    def __init__(self, hat=8, buttons=0, lx=127, ly=127, rx=127, ry=127):
        self.hat = hat
        self.buttons = buttons
        self._axes = [lx, ly, rx, ry]

    @property
    def axes(self):
        return self._axes

    @axes.setter
    def axes(self, axes):
        if len(axes) == 4 and all([isinstance(x, int) for x in axes]):
            self._axes = axes
        else:
            raise TypeError('Axes must be a list of four ints.')

    @property
    def bytes(self):
        """Returns the state as a raw byte string."""
        return struct.pack('>BHBBBB', self.hat, self.buttons, *self._axes)

    @property
    def hex(self):
        """Returns the state encoded as a hexadecimal byte string suitable for writing to a file or serial port."""
        return binascii.hexlify(self.bytes)

    @property
    def hexstr(self):
        """Returns the state encoded as a string suitable for printing."""
        return self.hex.decode('utf8')

    @classmethod
    def frombytes(cls, b):
        return cls(*struct.unpack('>BHBBBB', b))

    @classmethod
    def fromhex(cls, hex):
        return cls.frombytes(binascii.unhexlify(hex.strip()))

    @classmethod
    def all(cls):
        return cls(hat=0xff, buttons=0xffff, lx=0xff, ly=0xff, rx=0xff, ry=0xff)

    @classmethod
    def none(cls):
        return cls(hat=0, buttons=0, lx=0, ly=0, rx=0, ry=0)


    def __repr__(self):
        return '{:s}(hat=0x{:x}, buttons=0x{:x}, lx=0x{:x}, ly=0x{:x}, rx=0x{:x}, ry=0x{:x})'.format(
            type(self).__name__, self.hat, self.buttons, *self._axes
        )

    def __and__(self, other):
        return State(
            self.hat & other.hat,
            self.buttons & other.buttons,
            *[x&y for x, y in zip(self.axes, other.axes)]
        )

    def __xor__(self, other):
        return State(
            self.hat ^ other.hat,
            self.buttons ^ other.buttons,
            *[x^y for x, y in zip(self.axes, other.axes)]
        )

    def __or__(self, other):
        return State(
            self.hat | other.hat,
            self.buttons | other.buttons,
            *[x|y for x, y in zip(self.axes, other.axes)]
        )

    def __iand__(self, other):
        self.hat &= other.hat
        self.buttons &= other.buttons
        for x in range(len(self._axes)):
            self._axes[x] &= other._axes[x]
        return self

    def __ixor__(self, other):
        self.hat ^= other.hat
        self.buttons ^= other.buttons
        for x in range(len(self._axes)):
            self._axes[x] ^= other._axes[x]
        return self

    def __ior__(self, other):
        self.hat |= other.hat
        self.buttons |= other.buttons
        for x in range(len(self._axes)):
            self._axes[x] |= other._axes[x]
        return self

    def __invert__(self):
        return State(
            ~self.hat&0xff,
            ~self.buttons&0xffff,
            *[~x&0xff for x in self._axes]
        )


if __name__ == '__main__':
    # Some tests
    s = State()
    print(s)
    s.lx = 0x23
    print(s)
    s.axes = [1, 2, 3, 4]
    print(s)
    print(s^s)
    print(s.hex)
    print(State.fromhex(s.hex))
