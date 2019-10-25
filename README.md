# CircuitPython Virtual Pet
Virtual Pet / Tamgagotchi-like software written for CircuitPython

Written specifically for my CircuitPython badge device (https://github.com/neubauek/CircuitPythonBadge). Could be tailored to work with other CircuitPython devices with 3 buttons and an SD1306 or SH1106 OLED driver with 128x64 resolution. The native micropython framebuf library must be compiled in to your CircuitPython install. The Adafruit_framebuf python library didn't work well for this application.

Project inspired by Tamaduino (https://alojzjakob.github.io/Tamaguino/). Some logic was borrowed from their most excellent Arduino Tamagotchi clone.

Want to design your own pet?
Paint the screens using: https://www.pixilart.com
Use existing art under assets folder for size reference.
After painted, encode them in 0/1 format using: https://www.dcode.fr/binary-image