# The MIT License (MIT)
#
# Copyright (c) 2018 Mark Winney
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`sh1106`
====================================================

MicroPython SH1106 OLED driver, I2C and SPI interfaces

* Author(s): Mark Winney and heavily based on work by Tony DiCola, Michael McWethy
"""

import time

from micropython import const
import framebuf

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/winneymj/Adafruit_CircuitPython_SH1106.git"

#pylint: disable-msg=bad-whitespace
# register definitions
SET_CONTRAST            = const(0x81)
SET_ENTIRE_ON           = const(0xa4)
SET_DISP_ALLON          = const(0xa5)
SET_NORM                = const(0xa6)
SET_NORM_INV            = const(0xa7)
SET_DISP_OFF            = const(0xae)
SET_DISP_ON             = const(0xaf)
SET_MEM_ADDR            = const(0x20)
SET_COL_ADDR            = const(0x21)
SET_PAGE_ADDR           = const(0x22)
SET_PAGE_ADDRESS        = const(0xb0)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP       = const(0xa1)
SET_MUX_RATIO       = const(0xa8)
SET_COMSCANDEC      = const(0xc8)
SET_COMSCANINC      = const(0xc0)
SET_DISP_OFFSET     = const(0xd3)
SET_COM_PIN_CFG     = const(0xda)
SET_DISP_CLK_DIV    = const(0xd5)
SET_PRECHARGE       = const(0xd9)
SET_VCOM_DESEL      = const(0xdb)
SET_CHARGE_PUMP     = const(0x8d)
SET_LOW_COLUMN      = const(0x00)
SET_HIGH_COLUMN     = const(0x10)
#pylint: enable-msg=bad-whitespace


class _SH1106:
    """Base class for SH1106 display driver"""
    #pylint: disable-msg=too-many-arguments
    #pylint: disable-msg=too-many-instance-attributes
    def __init__(self, framebuffer, width, height, external_vcc, reset):
        self.framebuf = framebuffer
        self.fill = self.framebuf.fill
        self.pixel = self.framebuf.pixel
        self.line = self.framebuf.line
        self.text = self.framebuf.text
        self.scroll = self.framebuf.scroll
        self.blit = self.framebuf.blit
        self.vline = self.framebuf.vline
        self.hline = self.framebuf.hline
        self.fill_rect = self.framebuf.fill_rect
        self.rect = self.framebuf.rect
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        # reset may be None if not needed
        self.reset_pin = reset
        if self.reset_pin:
            self.reset_pin.switch_to_output(value=0)
        # Note the subclass must initialize self.framebuf to a framebuffer.
        # This is necessary because the underlying data buffer is different
        # between I2C and SPI implementations (I2C needs an extra byte).
        self.poweron()
        self.init_display()

    def init_display(self):
        """Base class to initialize display"""
        for cmd in (
                SET_DISP_OFF, # Display Off
                SET_DISP_CLK_DIV, 0xF0, # Ratio
                SET_MUX_RATIO, 0x3F, # Multiplex
                SET_DISP_OFFSET, 0x00, # No offset
                SET_DISP_START_LINE | 0x00, # Start line
                SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14, # Charge pump
                SET_MEM_ADDR, 0x00, # Memory mode, Horizontal
                SET_PAGE_ADDRESS, # Page address 0
                SET_COMSCANDEC, # COMSCANDEC
                SET_LOW_COLUMN, # SETLOWCOLUMN
                SET_HIGH_COLUMN, # SETHIGHCOLUMN
                SET_COM_PIN_CFG, 0x02 if self.height == 32 else 0x12, # SETCOMPINS
                SET_CONTRAST, 0x9f if self.external_vcc else 0xcf, # Contrast maximum
                SET_SEG_REMAP, # SET_SEGMENT_REMAP
                SET_PRECHARGE, 0x22 if self.external_vcc else 0xf1, # Pre Charge
                SET_VCOM_DESEL, 0x20, # VCOM Detect 0.77*Vcc
                SET_ENTIRE_ON, # DISPLAYALLON_RESUME
                SET_NORM, # NORMALDISPLAY
                SET_DISP_ON): # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        """Turn off the display (nothing visible)"""
        self.write_cmd(SET_DISP_OFF)

    def contrast(self, contrast):
        """Adjust the contrast"""
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        """Invert all pixels on the display"""
        if invert:
            self.write_cmd(SET_NORM_INV)
        else:
            self.write_cmd(SET_NORM)

    def write_framebuf(self):
        """Derived class must implement this"""
        raise NotImplementedError

    def write_cmd(self, cmd):
        """Derived class must implement this"""
        raise NotImplementedError

    def poweron(self):
        "Reset device and turn on the display."
        if self.reset_pin:
            self.reset_pin.value = 1
            time.sleep(0.001)
            self.reset_pin.value = 0
            time.sleep(0.010)
            self.reset_pin.value = 1
            time.sleep(0.010)
        self.write_cmd(SET_DISP_ON)

    def show(self):
        """Update the display"""
        self.write_framebuf()

class SH1106_I2C(_SH1106):
    """
    I2C class for SH1106

    :param width: the width of the physical screen in pixels,
    :param height: the height of the physical screen in pixels,
    :param i2c: the I2C peripheral to use,
    :param addr: the 8-bit bus address of the device,
    :param external_vcc: whether external high-voltage source is connected.
    :param reset: if needed, DigitalInOut designating reset pin
    """

    def __init__(self, width, height, i2c, *, addr=0x3c, external_vcc=False, reset=None):
        self.i2c_bus = i2c
        self.addr = addr
        self.temp = bytearray(2)
        # Add an extra byte to the data buffer to hold an I2C data/command byte
        # to use hardware-compatible I2C transactions.  A memoryview of the
        # buffer is used to mask this byte from the framebuffer operations
        # (without a major memory hit as memoryview doesn't copy to a separate
        # buffer).
        self.buffer = bytearray(((height // 8) * width) + 1)
        self.buffer[0] = 0x40  # Set first byte of data buffer to Co=0, D/C=1
        framebuffer = framebuf.FrameBuffer1(memoryview(self.buffer)[1:], width, height)
        super().__init__(framebuffer, width, height, external_vcc, reset)

    def write_cmd(self, cmd):
        """Send a command to the I2C device"""
        self.temp[0] = 0x00 # Co = 0, D/C = 0
        self.temp[1] = cmd
        self.i2c_bus.try_lock()
        self.i2c_bus.writeto(self.addr, self.temp)

    def write_framebuf(self):
        """write to the frame buffer via I2C"""

        self.i2c_bus.try_lock()
        write = self.i2c_bus.writeto
        write_cmd = self.write_cmd
        tmp_buf = bytearray(1)
        tmp_buf[0] = 0x40 # Co = 0, D/C = 1

        local_buffer = bytearray(self.width+1)

        for page in range(0, 8): # Pages
            page_mult = (page << 7)
            write_cmd(0xB0 + page) # set page address
            write_cmd(0x02) # set lower column address
            write_cmd(0x10) # set higher column address

            # Not sure if there is a way to do this without a local buffer
            # as we need to peprend a databyte onto the framebuffer data being sent.
            local_buffer = self.buffer[page_mult:page_mult + self.width + 2]
            local_buffer[:0] = tmp_buf # prepend Co = 0, D/C = 1

            write(self.addr, local_buffer)

        self.i2c_bus.unlock()

#pylint: disable-msg=too-many-arguments
class SH1106_SPI(_SH1106):
    """
    SPI class for SH1106

    :param width: the width of the physical screen in pixels,
    :param height: the height of the physical screen in pixels,
    :param spi: the SPI peripheral to use,
    :param dc: the data/command pin to use (often labeled "D/C"),
    :param reset: the reset pin to use,
    :param cs: the chip-select pin to use (sometimes labeled "SS").
    """
    # pylint: disable=no-member
    # Disable should be reconsidered when refactor can be tested.
    def __init__(self, width, height, spi, dc, reset, cs, *,
                 external_vcc=False, baudrate=8000000, polarity=0, phase=0):
        self.rate = 10 * 1024 * 1024
        dc.switch_to_output(value=0)
        cs.switch_to_output(value=1)
        self.spi_bus = spi
        self.spi_bus.try_lock()
        self.spi_bus.configure(baudrate=baudrate, polarity=polarity, phase=phase)
        self.spi_bus.unlock()
        self.dc_pin = dc
        self.buffer = bytearray((height // 8) * width)
        framebuffer = framebuf.FrameBuffer1(self.buffer, width, height)
        super().__init__(framebuffer, width, height, external_vcc, reset)

    def write_cmd(self, cmd):
        """Send a command to the SPI device"""
        self.dc_pin.value = 0
        self.spi_bus.try_lock()
        self.spi_bus.write(bytearray([cmd]))

    def write_framebuf(self):
        """write to the frame buffer via SPI"""

        self.spi_bus.try_lock()
        spi_write = self.spi_bus.write
        write = self.write_cmd

        for page in range(0, 8): # Pages
            page_mult = (page << 7)
            write(0xB0 + page) # set page address
            write(0x02) # set lower column address
            write(0x10) # set higher column address

            self.dc_pin.value = 1
            spi_write(self.buffer, start=page_mult, end=page_mult + self.width)

        self.spi_bus.unlock()
