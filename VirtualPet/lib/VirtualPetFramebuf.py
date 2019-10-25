# The MIT License (MIT)
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
`VirtualPetFramebuf.py`
====================================================

CircuitPython virtual pet framebuffer / wrapper class for virtual pet game
* Author(s): Kevin Neubauer
"""
import board
import busio
import sh1106
import time
import framebuf

WHITE = 1;
BLACK = 0;
SCRWIDTH = 128;
SCRHEIGHT = 64;

#initialize screen over I2C
i2c = busio.I2C(board.SCL, board.SDA)
display = sh1106.SH1106_I2C(SCRWIDTH, SCRHEIGHT, i2c, addr=0x3c)

class VirtualPetFramebuf:

    def __init__(self, intWidth, intHeight):
        self.height = intHeight;
        self.width = intWidth;
        bufsize = self.width * self.height // 8
        buf = bytearray(bufsize)
        for x in range(bufsize):
            buf[x] = 0
        self.framebuf = framebuf.FrameBuffer(buf, self.width, self.height, framebuf.MONO_VLSB)

    #function that takes 0 and 1 contents from a string and populates a framebuffer object
    def setContentsFromString(self, strBits, x_origin = 0, y_origin = 0):
        x = 0;
        y = 0;
        for bit in strBits:
            #print("x: " + str(x) + " y: " + str(y));
            self.framebuf.pixel((x + x_origin), (y + y_origin), int(bit))
            x = x + 1;
            if (x == self.width):
                y = y + 1;
                x = 0;

    #function that takes 0 and 1 contents from a list and populates a framebuffer object
    def setContentsFromList(self, listObj, x_origin = 0, y_origin = 0):
        pic = [line.rstrip('\r\n') for line in listObj]
        for y, row in enumerate(pic):
            for x, col in enumerate(row):
                #print("x: " + str(x) + " y: " + str(y) + " - " + str(col))
                self.framebuf.pixel((x + x_origin), (y + y_origin), int(col))

    #function that takes 0 and 1 contents from a file and populates a framebuffer object
    def setContentsFromFile(self, strFileName, x_origin = 0, y_origin = 0):
        pic = [line.rstrip('\r\n') for line in open(strFileName)]
        for y, row in enumerate(pic):
            for x, col in enumerate(row):
                self.framebuf.pixel((x + x_origin), (y + y_origin), int(col))

    #function to print framebuffer contents to console
    def consolePrint(self):
        for x in range(0, self.width):
            for y in range(0, self.height):
                print(self.framebuf.pixel(x, y), end='')
            print('')

    #function to print framebuffer contents on screen
    def screenPrint(self):
        for x in range(0, self.width):
            for y in range(0, self.height):
                display.pixel(x, y, self.framebuf.pixel(x, y));
        display.show();

    #function to transpose a framebuffer on top of another framebuffer
    def blit(self, objFramebuf, origin_x, origin_y):
        self.framebuf.blit(objFramebuf, origin_x, origin_y)

    #function to render a filled rectangle
    def fill_rect(self, x, y, width, height, color):
        self.framebuf.fill_rect(x, y, width, height, color)
        display.show()

    #function to render a hollow rectangle
    def rect(self, x, y, width, height, color):
        self.framebuf.rect(x, y, width, height, color)
        display.show()

    #function to render text
    def text(self, strText, x, y, color):
        self.framebuf.text(strText, x, y, color)
        display.show()

    #function to clear display
    def clearDisplay(self):
        self.framebuf.fill(BLACK);
        display.show();