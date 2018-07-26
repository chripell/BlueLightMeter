#!/usr/bin/python3

import buspirate as bp
import struct
import time


class AS726x:

    ADDR = 0x49
    SENSORTYPE_AS7262 = 0x3E
    SENSORTYPE_AS7263 = 0x3F
    DEVICE_TYPE = 0x00
    HW_VERSION = 0x01
    CONTROL_SETUP = 0x04
    INT_T = 0x05
    DEVICE_TEMP = 0x06
    LED_CONTROL = 0x07
    STATUS_REG = 0x00
    WRITE_REG = 0x01
    READ_REG = 0x02
    TX_VALID = 0x02
    RX_VALID = 0x01
    DEBUG = False

    def __init__(self, gain: int):
        self.addr = self.ADDR
        self.i2c = bp.I2C("/dev/ttyUSB0", bp.I2C_SPEED_100KHZ)
        self.hard_reset()
        self.ver = self.read_reg(self.HW_VERSION)
        if (self.ver != self.SENSORTYPE_AS7262 and
           self.ver != self.SENSORTYPE_AS7263):
            raise IOError("Cannot communicate")
        self.set_bulb_current(0b00)
        self.set_bulb(0)
        self.set_indicator_current(0b11)
        self.set_indicator(0)
        self.set_gain(gain)
        self.set_mode(3)

    def read_reg_(self, reg: int):
        r = self.i2c.cmd_recv(self.addr, reg, 1)[0]
        if self.DEBUG:
            print("RX %d=%d" % (reg, r))
        return r

    def write_reg_(self, reg: int, val: int):
        if self.DEBUG:
            print("TX %d=%d" % (reg, val))
        self.i2c.send(self.addr, [reg, val])

    def read_reg(self, reg: int):
        status = self.read_reg_(self.STATUS_REG)
        while status & self.RX_VALID:
            incoming = self.read_reg_(self.READ_REG)
            status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, reg)
        status = self.read_reg_(self.STATUS_REG)
        while status & self.RX_VALID == 0:
            status = self.read_reg_(self.STATUS_REG)
        incoming = self.read_reg_(self.READ_REG)
        return incoming

    def write_reg(self, reg: int, val: int):
        status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, reg | 0x80)
        status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, val)

    def set_bulb_current(self, current: int):
        if current > 0b11:
            current = 0b11
        value = self.read_reg(self.LED_CONTROL)
        value &= 0b11001111
        value |= (current << 4)
        self.write_reg(self.LED_CONTROL, value)

    # 0: 12.5mA
    # 1: 25mA
    # 2: 50mA
    # 3: 100mA
    def set_bulb(self, val: int):
        value = self.read_reg(self.LED_CONTROL)
        value &= ~(1 << 3)
        value |= (val << 3)
        self.write_reg(self.LED_CONTROL, value)

    def get_temperature(self):
        return self.read_reg(self.DEVICE_TEMP)

    # Max 8mA = 0b11
    def set_indicator_current(self, current: int):
        if current > 0b11:
            current = 0b11
        value = self.read_reg(self.LED_CONTROL)
        value &= 0b11111001
        value |= (current << 1)
        self.write_reg(self.LED_CONTROL, value)

    def set_indicator(self, val: int):
        value = self.read_reg(self.LED_CONTROL)
        value &= ~(1 << 0)
        value |= (val << 0)
        self.write_reg(self.LED_CONTROL, value)

    # Gain 0: 1x (power-on default)
    # Gain 1: 3.7x
    # Gain 2: 16x
    # Gain 3: 64x
    def set_gain(self, gain: int):
        if gain > 0b11:
            gain = 0b11
        value = self.read_reg(self.CONTROL_SETUP)
        value &= 0b11001111
        value |= (gain << 4)
        self.write_reg(self.CONTROL_SETUP, value)

    # Give this function a byte from 0 to 255.
    # Time will be 2.8ms * [integration value]
    def set_integration(self, val: int):
        self.write_reg(self.INT_T, val)

    def measure(self):
        self.clear_data()
        self.set_mode(3)
        while not self.has_data():
            pass

    def get_channel(self, addr: int):
        data = self.read_reg(addr) << 8
        data |= self.read_reg(addr + 1)
        return data

    def get_calibrated(self, addr: int):
        return struct.unpack(
            "f",
            struct.pack(
                "BBBB",
                self.read_reg(addr + 3),
                self.read_reg(addr + 2),
                self.read_reg(addr + 1),
                self.read_reg(addr + 0)))[0]

    def has_data(self):
        value = self.read_reg(self.CONTROL_SETUP)
        return value & (1 << 1)

    def clear_data(self):
        value = self.read_reg(self.CONTROL_SETUP)
        value &= ~(1 << 1)
        self.write_reg(self.CONTROL_SETUP, value)

    def soft_reset(self):
        value = self.read_reg(self.CONTROL_SETUP)
        value |= (1 << 7)
        self.write_reg(self.CONTROL_SETUP, value)
        time.sleep(1)

    # Reset must be wired to Buspirate CS
    def hard_reset(self):
        self.i2c.set_pin(0, 0)
        time.sleep(1)
        self.i2c.set_pin(1, 1)
        time.sleep(1)

    # Mode 0: Continuous reading of VBGY (7262) / STUV (7263)
    # Mode 1: Continuous reading of GYOR (7262) / RTUX (7263)
    # Mode 2: Continuous reading of all channels (power-on default)
    # Mode 3: One-shot reading of all channels
    def set_mode(self, mode: int):
        if mode > 0b11:
            mode = 0b11
        value = self.read_reg(self.CONTROL_SETUP)
        value &= 0b11110011
        value |= (mode << 2)
        self.write_reg(self.CONTROL_SETUP, value)

    def get_all_values(self):
        return [
            self.get_calibrated(0x14),
            self.get_calibrated(0x18),
            self.get_calibrated(0x1c),
            self.get_calibrated(0x20),
            self.get_calibrated(0x24),
            self.get_calibrated(0x28)]


as726x = AS726x(3)
# as726x.set_bulb(1)
as726x.measure()
print(as726x.get_all_values())
# as726x.set_bulb(0)
