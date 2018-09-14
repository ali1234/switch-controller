import binascii
import ctypes
import fcntl
import logging
import os
import select
import struct
import time

import functionfs
from functionfs import USB_DIR_IN, USB_TYPE_MASK, USB_TYPE_STANDARD, USB_RECIP_MASK, USB_REQ_GET_STATUS, \
    USB_RECIP_INTERFACE, USB_RECIP_ENDPOINT, USB_REQ_CLEAR_FEATURE, USB_ENDPOINT_HALT, USB_REQ_SET_FEATURE
from functionfs.ch9 import USB_REQ_GET_DESCRIPTOR, USB_REQ_SET_CONFIGURATION

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


udc_eps = {
    'dummy_udc': ['ep1in-bulk', 'ep2out-bulk'],
    '20980000.usb': ['ep1in', 'ep2out'],
}

class Gadget(functionfs.Function):

    def __init__(self, udc, device_params, device_strings, report_desc):

        self.udc = udc

        self.report_desc = report_desc
        self.device_strings = device_strings
        self._report_requested = False

        self.devdes = functionfs.getDescriptor(
            functionfs.ch9.USBDeviceDescriptor,
            **{k: int(v, 16) for k, v in device_params.items()},
            bMaxPacketSize0=255,
            iManufacturer=1,
            iProduct=2,
            iSerialNumber=0,
            bNumConfigurations=1,
        )

        self.intdes = functionfs.getDescriptor(
            functionfs.USBInterfaceDescriptor,
            bInterfaceNumber=0,
            bAlternateSetting=0,
            bNumEndpoints=2,
            bInterfaceClass=functionfs.ch9.USB_CLASS_HID,
            bInterfaceSubClass=0,
            bInterfaceProtocol=0,
            iInterface=0,
        )

        self.hiddes = functionfs.getDescriptor(
            USBHIDDescriptor,
            bcdHID=0x0111,
            bCountryCode=0,
            bNumDescriptors=1,
            bDescriptorxType=34,
            wDescriptorLength=len(self.report_desc),
        )

        self.ep1des = functionfs.getDescriptor(
            functionfs.USBEndpointDescriptorNoAudio,
            bEndpointAddress=1 | functionfs.ch9.USB_DIR_IN,
            bmAttributes=functionfs.ch9.USB_ENDPOINT_XFER_INT,
            wMaxPacketSize=64,
            bInterval=5,
        )

        self.ep2des = functionfs.getDescriptor(
            functionfs.USBEndpointDescriptorNoAudio,
            bEndpointAddress=2 | functionfs.ch9.USB_DIR_OUT,
            bmAttributes=functionfs.ch9.USB_ENDPOINT_XFER_INT,
            wMaxPacketSize=64,
            bInterval=5,
        )

        self.confdes = functionfs.getDescriptor(
            functionfs.ch9.USBConfigDescriptor,
            wTotalLength=0x29,
            bNumInterfaces=1,
            bConfigurationValue=1,
            iConfiguration=0,
            bmAttributes=functionfs.ch9.USB_CONFIG_ATT_ONE,
            bMaxPower=125,
        )

        self._path = '/dev/gadget'
        ep0 = functionfs.Endpoint0File(os.path.join(self._path, udc), 'r+')
        self._ep_list = [ep0]
        self._ep_address_dict = {}


        descs = b''.join(bytes(x) for x in [
            b'\x00\x00\x00\x00',
            self.confdes,
            self.intdes,
            self.hiddes,
            self.ep1des,
            self.ep2des,
            self.confdes,
            self.intdes,
            self.hiddes,
            self.ep1des,
            self.ep2des,
            self.devdes,
        ])

        self.ep0.write(descs)
        logger.warning('go')
        # set ep0 to non-blocking
        orig_fl = fcntl.fcntl(self.ep0, fcntl.F_GETFL)
        fcntl.fcntl(self.ep0, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)


    def onSetup(self, request_type, request, value, index, length):
        if (request_type & USB_TYPE_MASK) == USB_TYPE_STANDARD:
            if request == USB_REQ_SET_CONFIGURATION:
                # ack
                self.ep0.read(0)

                # now we can open the interrupt endpoints
                ep1s = b''.join(bytes(x) for x in [
                    b'\x01\x00\x00\x00',
                    self.ep1des,
                    self.ep1des,
                ])

                ep2s = b''.join(bytes(x) for x in [
                    b'\x01\x00\x00\x00',
                    self.ep2des,
                    self.ep2des,
                ])

                ep1 = functionfs.EndpointINFile('/dev/gadget/' + udc_eps[self.udc][0], 'r+')
                ep1.write(ep1s)
                self._ep_list.append(ep1)

                ep2 = functionfs.EndpointINFile('/dev/gadget/' + udc_eps[self.udc][1], 'r+')
                ep2.write(ep2s)
                self._ep_list.append(ep2)

                return

            elif request == USB_REQ_GET_DESCRIPTOR:
                descindex = value &0xff
                desctype = value>>8
                logger.warning('get descriptor {:02x} {:02x} {:02x} {:02x} {:02x} {:02x}'.format(request_type, request, descindex, desctype, index, length))
                if desctype == 0x22 and descindex == 0:
                    # send HID report descriptor
                    self.ep0.write(self.report_desc)
                    self._report_requested = True
                    return
                elif desctype == 0x03:
                    if descindex == 0:
                        self.ep0.write(b'\x04\x03\x09\x04')
                        return
                    elif descindex == 1:
                        s = self.device_strings['manufacturer'].encode('utf_16_le')
                        l = 2+len(s)
                        hdr = struct.pack('<BB', l, 3)
                        self.ep0.write(hdr + s)
                        return
                    elif descindex == 2:
                        s = self.device_strings['product'].encode('utf_16_le')
                        l = 2+len(s)
                        hdr = struct.pack('<BB', l, 3)
                        self.ep0.write(hdr + s)
                        return

        logger.warning('Unhandled setup request {:02x} {:02x} {:02x} {:02x} {:02x}'.format(request_type, request, value, index, length))
        super().onSetup(request_type, request, value, index, length)

    def processEvents(self):
        req = self.ep0.read(12)
        if req is not None and len(req) == 12:
            (ev,) = struct.unpack('<I', req[8:])
            setup = struct.unpack('<BBHHH', req[:8])
            if ev == 3:
                self.onSetup(*setup)


if __name__ == '__main__':
    with Gadget() as g:
        while True:
            g.poll()

