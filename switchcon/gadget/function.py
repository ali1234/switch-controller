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

import ctypes
import fcntl
import logging
import os

import functionfs
import functionfs.ch9


u8 = ctypes.c_ubyte
assert ctypes.sizeof(u8) == 1
le16 = ctypes.c_ushort
assert ctypes.sizeof(le16) == 2
le32 = ctypes.c_uint
assert ctypes.sizeof(le32) == 4

logger = logging.getLogger(__name__)


class USBHIDDescriptor(functionfs.USBDescriptorHeader):
    """
    USB_DT_HID: HID descriptor
    """
    _bDescriptorType = 33
    _fields_ = [
        ('bcdHID', le16),
        ('bCountryCode', u8),
        ('bNumDescriptors', u8),
        ('bDescriptorxType', u8),
        ('wDescriptorLength', le16),
    ]


class HIDFunction(functionfs.Function):
    def __init__(self, gadget, report_desc):

        self.gadget = gadget
        self.report_desc = report_desc

        self._report_requested = False

        descriptors = [

            functionfs.getDescriptor(
                functionfs.USBInterfaceDescriptor,
                bInterfaceNumber=0,
                bAlternateSetting=0,
                bNumEndpoints=2,
                bInterfaceClass=functionfs.ch9.USB_CLASS_HID,
                bInterfaceSubClass=0,
                bInterfaceProtocol=0,
                iInterface=1,
            ),

            functionfs.getDescriptor(
                USBHIDDescriptor,
                bcdHID=0x0111,
                bCountryCode=0,
                bNumDescriptors=1,
                bDescriptorxType=34,
                wDescriptorLength=len(self.report_desc),
            ),

            functionfs.getDescriptor(
                functionfs.USBEndpointDescriptorNoAudio,
                bEndpointAddress=1 | functionfs.ch9.USB_DIR_IN,
                bmAttributes=functionfs.ch9.USB_ENDPOINT_XFER_INT,
                wMaxPacketSize=64,
                bInterval=5,
            ),

            functionfs.getDescriptor(
                functionfs.USBEndpointDescriptorNoAudio,
                bEndpointAddress=2 | functionfs.ch9.USB_DIR_OUT,
                bmAttributes=functionfs.ch9.USB_ENDPOINT_XFER_INT,
                wMaxPacketSize=64,
                bInterval=5,
            )
        ]

        super().__init__(
            self.gadget.mount_point,
            fs_list=descriptors,
            hs_list=descriptors,
            lang_dict={
                0x0409: [
                    u'HID Interface',
                ],
            },
        )

        # set ep0 to non-blocking
        orig_fl = fcntl.fcntl(self.ep0, fcntl.F_GETFL)
        fcntl.fcntl(self.ep0, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

    def onSetup(self, request_type, request, value, index, length):
        logger.debug('Setup request {} {} {} {} {}'.format(request_type, request, value, index, length))
        if request_type == 0x81 and request == 0x6 and value == 0x2200 and index == 0 and length == len(
                self.report_desc):
            # send HID report descriptor
            self.ep0.write(self.report_desc)
            self._report_requested = True
        else:
            super().onSetup(request_type, request, value, index, length)
