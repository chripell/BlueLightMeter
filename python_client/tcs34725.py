#!/usr/bin/python3

import buspirate as bp
from time import sleep


class TCS34725:

    def __init__(self):
        self.addr = 0x29
        self.i2c = bp.I2C("/dev/ttyUSB0", bp.I2C_SPEED_50KHZ)
        self.i2c.set_pin(0, 0)

    def light(self, on: int):
        if on != 0:
            on = 1
        self.i2c.set_pin(on, on)

    def write_reg(self, reg: int, val: int):
        self.i2c.send(self.addr, [0xa0 | reg, val])

    def read_reg(self, reg: int, n: int):
        return self.i2c.cmd_recv(self.addr, 0xa0 | reg, n)

    def power_on(self):
        self.write_reg(0, 1)
        sleep(0.0024)
        self.write_reg(0xd, 0)

    def start(self):
        self.write_reg(0, 3)

    def integration_ms(self, t: int):
        t = int(t / 2.4)
        if t > 255:
            t = 255
        self.write_reg(1, 255 - t)

    def gain(self, g: int):
        if g < 0:
            g = 0
        if g > 3:
            g = 3
        self.write_reg(0xf, g)

    def read_crgb(self):
        status = self.read_reg(0x13, 1)
        while status[0] & 1 == 0:
            status = self.read_reg(0x13, 1)
        data = self.read_reg(0x14, 8)
        return [
            data[0] + data[1] * 256,
            data[2] + data[3] * 256,
            data[4] + data[5] * 256,
            data[6] + data[7] * 256,
        ]

    def dump(self):
        data = self.read_reg(0, 0x1b + 1)
        for i, v in enumerate(data):
            print("0x{:0>2x}=0x{:0>2x}".format(i, v))


tcs34725 = TCS34725()
tcs34725.power_on()
tcs34725.gain(2)
tcs34725.integration_ms(100)
tcs34725.start()
tcs34725.dump()
while True:
    print("{0[0]:0>5d} {0[1]:0>5d} {0[2]:0>5d} {0[3]:0>5d}".format(
        tcs34725.read_crgb()), end="\r")
