#!/usr/bin/env python

import dbus
import argparse
import time
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Handles a BlueLightMeter.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--mac_address', '-m', type=str, nargs='?',
                   help='MAC address of BlueLightMeter, discover if not present.')
parser.add_argument('--hci_interface', '-i', type=str, nargs='?', default='hci0',
                   help='HCI interface to use, default hci0.')
parser.add_argument('--timeout', '-t', type=int, nargs='?', default=10,
                   help='Timeout for scan,connect, etc..')
parser.add_argument('--name', '-n', type=str, nargs='?', default='RFduino',
                   help='Name advertised by BlueLightMeter')
args = parser.parse_args()


class BLM:

    BLUEZ_PATH = '/org/bluez'
    BLUEZ = 'org.bluez'

    def __init__(self):
        hci_path = self.BLUEZ_PATH + '/' + args.hci_interface
        bus = dbus.SystemBus(self.BLUEZ)
        hci = bus.get_object(self.BLUEZ, hci_path)

        self.blm_ = None
        checked = []
        hci.StartDiscovery(dbus_interface='org.bluez.Adapter1')
        if args.mac_address == None:
            print('Scanning for BlueLightMeter')
            start = time.time()
            while time.time() < start + args.timeout and not self.blm_:
                root = ET.fromstring(hci.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable'))
                time.sleep(1)
                for ch in root:
                    if ch.tag == 'node':
                        dname = ch.attrib['name']
                        if dname and not dname in checked:
                            checked.append(dname)
                            path = hci_path +'/' + dname
                            dev = bus.get_object(self.BLUEZ, path)
                            devp = dbus.Interface(dev, 'org.freedesktop.DBus.Properties')
                            name = devp.Get('org.bluez.Device1', 'Name')
                            if name == args.name:
                                print('Found: %s' % dname[4:].replace('_', ':'))
                                self.path_ = path
                                self.blm_ = dev
                                self.blmp_ = devp
                                self.blmd_ = dbus.Interface(dev, 'org.bluez.Device1')
                                break
        else:
            print('Connecting to BlueLightMeter with MAC %s' % args.mac_address)
            path = hci_path +'/dev_' + args.mac_address.replace(':', '_')
            self.blm_ = bus.get_object(self.BLUEZ, path)
            self.blmp_ = dbus.Interface(self.blm_, 'org.freedesktop.DBus.Properties')
            self.blmd_ = dbus.Interface(self.blm_, 'org.bluez.Device1')

        self.blmd_.Connect()
        self.connected_ = False
        start = time.time()
        while time.time() < start + args.timeout and not self.connected_:
            self.connected_ = self.prop_get('Connected')
        if not self.connected_:
            print("Failed to connect")
            self.blmd_.Disconnect()
        print("Connected")

        gatt_read_path = self.path_ + '/service000c/char000d'
        gatt_read = bus.get_object(self.BLUEZ, gatt_read_path)
        self.gatt_read_ = dbus.Interface(gatt_read, 'org.bluez.GattCharacteristic1')

    def prop_get(self, prop):
        return self.blmp_.Get('org.bluez.Device1', prop)

    def close(self):
        self.blmd_.Disconnect()
        print("Disconnected")

    def read(self):
        raw = self.gatt_read_.ReadValue()
        return raw


blm = BLM()
for i in range(5):
    print(blm.read())
    time.sleep(1)
blm.close()
