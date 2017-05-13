#!/usr/bin/python2

import dbus
import argparse
import xml.etree.ElementTree as ET
import time

parser = argparse.ArgumentParser(description='Handles a Nordic virtual UART over BLE.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--mac_address', '-m', type=str, nargs='?',
                   help='MAC address, discover if not present.')
parser.add_argument('--hci_interface', '-i', type=str, nargs='?', default='hci0',
                   help='HCI interface to use, default hci0.')
parser.add_argument('--timeout', '-t', type=int, nargs='?', default=10,
                   help='Timeout for scan,connect, etc..')
parser.add_argument('--name', '-n', type=str, nargs='?', default='PureEngineering-CoreModule',
                   help='Name to llok for while scanning if no MAC specified.')
args = parser.parse_args()

class NordicUART(object):

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
            print 'Scanning for ', args.name
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
            print('Connecting to MAC %s' % args.mac_address)
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
            print('Failed to connect')
            self.blmd_.Disconnect()
        print('Connected')

        gatt_read_path = self.path_ + '/service000b/char000c'
        gatt_read = bus.get_object(self.BLUEZ, gatt_read_path)
        self.gatt_read_ = dbus.Interface(gatt_read, 'org.bluez.GattCharacteristic1')
        self.gatt_read_.StartNotify()

        gatt_write_path = self.path_ + '/service000b/char000f'
        gatt_write = bus.get_object(self.BLUEZ, gatt_write_path)
        self.gatt_write_ = dbus.Interface(gatt_write, 'org.bluez.GattCharacteristic1')
        
    def prop_get(self, prop):
        return self.blmp_.Get('org.bluez.Device1', prop)

    def read(self):
        return ''.join([chr(i) for i in self.gatt_read_.ReadValue({})])
    
    def write(self, data):
        self.gatt_write_.WriteValue([ord(i) for i in data], {})
    
    def close(self):
        self.blmd_.Disconnect()
        print('Disconnected')

            
uart = NordicUART()
for i in '13579bdf':
    uart.write(i)
print "Press CTRL-C to stop"
try:
    while True:
        print(uart.read())
except KeyboardInterrupt:
    pass
for i in '2468aceg':
    uart.write(i)
uart.close()
