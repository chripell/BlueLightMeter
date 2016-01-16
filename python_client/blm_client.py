#!/usr/bin/env python2

# Bluetooth (BLM)
import dbus
import argparse
import time
import xml.etree.ElementTree as ET
import time
import math
# GUI and everything else
from multiprocessing import Process, Queue
import pygtk
pygtk.require('2.0')
import gtk
import gobject

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
            print('Failed to connect')
            self.blmd_.Disconnect()
        print('Connected')
        time.sleep(3)

        gatt_read_path = self.path_ + '/service000c/char000d'
        gatt_read = bus.get_object(self.BLUEZ, gatt_read_path)
        self.gatt_read_ = dbus.Interface(gatt_read, 'org.bluez.GattCharacteristic1')

        gatt_write_path = self.path_ + '/service000c/char0010'
        gatt_write = bus.get_object(self.BLUEZ, gatt_write_path)
        self.gatt_write_ = dbus.Interface(gatt_write, 'org.bluez.GattCharacteristic1')

    def prop_get(self, prop):
        return self.blmp_.Get('org.bluez.Device1', prop)

    def close(self):
        self.blmd_.Disconnect()
        print('Disconnected')

    def read(self):
        raw = self.gatt_read_.ReadValue()
        if raw[0] == 0x11:
            return {
                'ch0' : raw[2] + raw[3] * 256,
                'ch1' : raw[4] + raw[5] * 256,
                'mode': raw[6] & 0x3,
                'higain': (raw[6] & 0x10) > 0,
                'int_time': raw[7] + raw[8] * 256}

    def write(self, conf):
        mode = conf['mode']
        if 'higain' in conf and conf['higain']:
            mode += 0x10
        int_time = conf.get('int_time', 0)
        self.gatt_write_.WriteValue([mode, int_time % 256, int_time // 256])
        

class BLMThread(Process):

  DEFAULT_MIN=100
  DEFAULT_MAX=5000
  PROFILES={
      'all': {
          'min': DEFAULT_MIN, 'max': DEFAULT_MAX,
          'v': [[False, 0], [False, 1], [True, 0], [False, 2], [True, 1], [True, 2]]},
      'fast': {
          'min': DEFAULT_MIN, 'max': DEFAULT_MAX,
          'v': [[False, 0], [True, 0], [True, 1], [True, 2]]},
      'logain': {
          'min': DEFAULT_MIN, 'max': DEFAULT_MAX,
          'v': [[False, 0], [False, 1], [False, 2], [True, 2]]}}
  MEAN_TIME_S = 3.0

  def __init__(self, cmds, lux):
    self.cmds = cmds
    self.lux = lux
    self.profile = 'manual'
    self.pstep = 0
    self.plast = 0.0
    self.med = []
    self.new_profile = True
    self.prev_profile = 'none'
    Process.__init__(self)

  def calc_lux(self):
      d0 = self.ch0
      d1 = self.ch1
      if d0 == 0xffff or d1 == 0xffff:
          return -1.0
      if d0 == 0 or d1 == 0:
          return 0.0
      ratio = float(d1) / d0
      d0 *= 402.0 / self.ms
      d1 *= 402.0 / self.ms
      if not self.higain:
          d0 *= 16.0
          d1 *= 16.0
      if ratio < 0.5:
          return 0.0304 * d0 - 0.062 * d0 * math.pow(ratio, 1.4)
      if ratio < 0.61:
          return 0.0224 * d0 - 0.031 * d1;
      if ratio < 0.80:
          return 0.0128 * d0 - 0.0153 * d1;
      if ratio < 1.30:
          return 0.00146 * d0 - 0.00112 * d1;
      return 0.0;

  def calc_max_lux(self, lux):
      now = time.time()
      self.med.append((now, lux))
      i = 0
      while self.med[i][0] < now - self.MEAN_TIME_S:
          i += 1
      self.med = self.med[i:]
      all_lux = [x[1] for x in self.med]
      self.max_lux = max(all_lux)
      self.med_lux = sum(all_lux) / float(len(all_lux))

  def next_step(self):
      try:
          cp = self.PROFILES[self.profile]
      except:
          self.new_profile = True
          return None
      if self.profile != self.prev_profile:
          self.prev_profile = self.profile
          self.new_profile = True
      now = time.time()
      ch = self.new_profile
      while self.pstep >= len(cp['v']):
          self.pstep -= 1
      if now > self.plast + 1.0:
          if ((self.ch0 < cp['min'] or self.ch1 < cp['min'])
              and self.pstep < (len(cp['v']) - 1)):
              self.pstep += 1
              ch = True
          if ((self.ch0 > cp['max'] or self.ch1 > cp['max'])
              and self.pstep > 0):
              self.pstep -= 1
              ch = True
          self.plast = now
      if ch:
          self.new_profile = False
          return {'higain': cp['v'][self.pstep][0],
                  'mode': cp['v'][self.pstep][1]}
      return None

  def run(self):
    blm = BLM()
    while True:
        
        state = blm.read()
        self.ch0 = state['ch0']
        self.ch1 = state['ch1']
        if state['mode'] == 0:
            self.ms = 13.7
        elif state['mode'] == 1:
            self.ms = 101.0
        elif state['mode'] == 2:
            self.ms = 402.0
        else:
            self.ms = state['int_time']
        self.higain = state['higain']
        lux = self.calc_lux()
        self.calc_max_lux(lux)
        try:
            self.lux.put_nowait({'lux': lux,
                                 'max_lux': self.max_lux,
                                 'med_lux': self.med_lux,
                                 'state': state})
        except:
            pass

        next_state = self.next_step()
        if next_state:
            blm.write(next_state)

        try:
            cmd = self.cmds.get_nowait()
        except:
            cmd = None
        if cmd:
            if cmd['cmd'] == 'quit':
                break
            if cmd['cmd'] == 'set':
                self.profile = cmd.get('profile', 'manual')
                if self.profile == 'manual':
                    blm.write(cmd)
                    
    blm.close()


class GUI:

    AVc = ('1', '1.4', '2', '2.8', '4', '5.6', '8', '11', '16', '22', '32')
    TVc = ('30', '15', '8', '4', '2', '1', '1/2', '1/4', '1/8', '1/15', '1/30', '1/60', '1/125', '1/250', '1/500', '1/1000', '1/2000', '1/4000', '1/8000')
    ISOc = ('100', '200', '400', '800', '1600', '3200', '6400')

    def setter(self, widget, key, value):
        if widget and not widget.get_active():
            return
        if key:
            self.mode[key] = value
        self.mode['int_time'] = int(self.int_time.get_text())
        try:
            self.cmds.put_nowait(self.mode)
            self.need_to_set = False
        except:
            self.need_to_set = True
        
    def destroy(self, widget, data=None):
        gtk.main_quit()

    def new_val(self, label, where):
        hbox = gtk.VBox()
        frame = gtk.Frame()
        frame.add(hbox)
        where.pack_start(frame)
        hbox.pack_start(gtk.Label(label))
        val = gtk.Label('<span size="38000">0.0</span>')
        val.set_use_markup(gtk.TRUE)
        hbox.pack_start(val)
        return val

    def new_choices(self, where, what, vals, act):
        self.but_choices[what] = []
        c = gtk.VBox()
        where.pack_start(c)
        first = None
        for label, setto in vals:
            but = gtk.RadioButton(first, label)
            self.but_choices[what].append(but)
            if not first:
                first = but
            if label == act:
                but.set_active(True)
            but.connect('toggled', self.setter, what, setto)
            c.pack_start(but)
            
    def process_lux(self, queue):
        if self.need_to_set:
            self.setter(None, None, None)
        try:
            data = queue.get_nowait()
        except:
            data = None
        if data:
            s = data['state']
            self.debug.set_text('ch: %d,%d mode: %d %s int: %d' %
                                (s['ch0'], s['ch1'], s['mode'], ('lo', 'hi')[s['higain']],
                                 s['int_time']))
            if self.first_data:
                self.higain.set_active(s['higain'])
                self.but_choices['mode'][s['mode']].set_active(True)
                self.int_time.set_text('%d' % s['int_time'])
                self.first_data = False
            self.cur_lux.set_markup('<span size="38000">%.2f</span>' % data['med_lux'])
            self.max_lux.set_markup('<span size="38000">%.2f</span>' % data['max_lux'])
            if data['med_lux'] <= 0.0:
                self.ev = -100
            else:
                self.ev = math.log(float(data['med_lux']) / 2.5, 2) 
            if data['max_lux'] <= 0.0:
                self.ev_max = -100
            else:
                self.ev_max = math.log(float(data['max_lux']) / 2.5, 2) 
            self.cur_ev.set_markup('<span size="38000">%.1f</span>' % self.ev)
            self.max_ev.set_markup('<span size="38000">%.1f</span>' % self.ev_max)
            self.calc_goal()
        return True

    def create_list(self, l, name, where):
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        clist = gtk.CList(1, (name,))
        scrolled_window.add(clist)
        clist.set_selection_mode(gtk.SELECTION_BROWSE)
        for i in l:
            row = clist.append(i)
            clist.set_text(row, 0, i)
        clist.connect('select_row', self.exp_setter, name)
        self.exp_setter(clist, 0, 0, None, name)
        where.pack_start(scrolled_window)

    def exp_setter(self, clist, row, column, event, name):
        setattr(self, name, self.make_float(clist.get_text(row, 0)))

    def toggle_obj(self, widget, obj, o):
        if widget.get_active():
            setattr(self, obj, o)

    def create_obj(self, obj, o, where):
        base = getattr(self, obj + '_base')
        but = gtk.RadioButton(base, o)
        if not base:
            setattr(self, obj + '_base', but)
        where.pack_start(but)
        but.connect('toggled', lambda w: self.toggle_obj(w, obj, o))

    def make_float(self, v):
        if v.startswith('1/'):
            return 1.0 / float(v[2:])
        return float(v)

    def find_nearer(self, val, l):
        min = 1e10
        ret = l[0]
        for i in l:
            diff = math.fabs(self.make_float(i) - val)
            if diff < min:
                ret = i
                min = diff
        return ret

    def calc_ev(self, av, tv):
        return math.log(math.pow(av, 2.0) / tv, 2.0)

    def calc_goal(self):
        if self.which == 'Flash':
            ev = self.ev_max
        else:
            ev = self.ev
        if self.what == 'Av' or self.what == 'Tv':
            delta_ev = math.log(self.ISO / 100.0, 2.0)
            ev += delta_ev
            ev2 = math.pow(2.0, ev)
            if self.what == 'Tv':
                tv = math.pow(self.Av, 2.0) / ev2
                tvn = self.find_nearer(tv, self.TVc)
                self.goal.set_markup('<span size="38000">%s s</span>' % tvn)
                self.goal_ev.set_text('Ev=%.1f' %
                                      (self.calc_ev(self.Av, self.make_float(tvn)) - delta_ev))
            elif self.what == 'Av':
                av = math.sqrt(ev2 * self.Tv)
                avn = self.find_nearer(av, self.AVc)
                self.goal.set_markup('<span size="38000">f/%s</span>' % avn)
                self.goal_ev.set_text('Ev=%.1f' %
                                      (self.calc_ev(float(avn), self.Tv) - delta_ev))
        elif self.what == 'ISO':
            evb = self.calc_ev(self.Av, self.Tv)
            isov = math.pow(2.0, evb - ev) * 100.0
            isovn = self.find_nearer(isov, self.ISOc)
            self.goal.set_markup('<span size="38000">%s ISO</span>' % isovn)
            self.goal_ev.set_text('Ev=%.1f' %
                                  (evb + math.log(float(isovn) / 100.0, 2.0)))
        
    def __init__(self, cmds, lux):
        self.first_data = True
        self.need_to_set = False
        self.cmds = cmds
        self.mode = {
            'cmd' : 'set',
            'profile' : 'manual',
            'mode' : 2,
            'higain' : False,
            'int_time': 500}
        self.ev = 1.0
        self.ev_max = 1.0
        
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('destroy', self.destroy)
        self.window.set_title('BlueLightMeter')
        self.window.set_geometry_hints(min_width=400, min_height=500)

        vals = gtk.VBox()
        self.window.add(vals)
        cur = gtk.HBox()
        vals.pack_start(cur)
        self.cur_lux = self.new_val('Cur Lux:', cur)
        self.cur_ev = self.new_val('EV:', cur)
        max = gtk.HBox()
        vals.pack_start(max)
        self.max_lux = self.new_val('Max Lux:', max)
        self.max_ev = self.new_val('EV:', max)
        self.debug = gtk.Label('Debug Info')
        vals.pack_start(self.debug)
        
        ctrl = gtk.HBox()
        frame = gtk.Frame()
        frame.add(ctrl)
        vals.pack_start(frame)
        ctrl_left = gtk.VBox()
        ctrl.pack_start(ctrl_left)
        ctrl_right = gtk.VBox()
        ctrl.pack_start(ctrl_right)

        self.but_choices = {}
        self.new_choices(ctrl_left, 'profile',
                         (('Manual', 'manual'), ('All Values', 'all'),
                          ('Fast Modes', 'fast'), ('Low gain', 'logain')), 'Manual')
        self.higain = gtk.CheckButton('High Gain')
        ctrl_left.pack_start(self.higain)
        self.higain.connect('toggled', lambda w: self.setter(None, 'higain', w.get_active()))

        self.new_choices(ctrl_right, 'mode',
                         (('13.7 ms', 0), ('101 ms', 1), ('402 ms', 2), ('Custom:', 3)),
                         '402 ms')
        self.int_time = gtk.Entry()
        self.int_time.set_width_chars(6)
        ctrl_right.pack_start(self.int_time)
        self.int_time.set_text('500')
        self.int_time.connect('activate', lambda w: self.setter(None, None, None))

        calc = gtk.VBox()
        frame = gtk.Frame()
        vals.pack_start(frame)
        frame.add(calc)
        
        calc_inputs = gtk.HBox()
        calc.pack_start(calc_inputs, expand=True)
        self.create_list(self.AVc, 'Av', calc_inputs)
        self.create_list(self.TVc, 'Tv', calc_inputs)
        self.create_list(self.ISOc, 'ISO', calc_inputs)
        
        calc_outputs = gtk.HBox()
        calc.pack_start(calc_outputs, expand=False)
        
        which = gtk.VBox()
        calc_outputs.pack_start(which)
        which.pack_start(gtk.Label('Calculate:'))
        self.which = 'Normal'
        self.which_base = None        
        self.create_obj('which', 'Normal', which)
        self.create_obj('which', 'Flash', which)
        
        what = gtk.VBox()
        calc_outputs.pack_start(what)
        self.what = 'Tv'
        self.what_base = None
        self.create_obj('what', 'Tv', what)
        self.create_obj('what', 'Av', what)
        self.create_obj('what', 'ISO', what)
        
        goals = gtk.VBox()
        calc_outputs.pack_start(goals)
        self.goal = gtk.Label('<span size="38000">???</span>')
        self.goal.set_use_markup(gtk.TRUE)
        goals.pack_start(self.goal)
        self.goal_ev = gtk.Label('Ev=???')
        goals.pack_start(self.goal_ev)

        self.window.show_all()
        gobject.idle_add(lambda: self.process_lux(lux))

    def main(self):
        gtk.main()

if __name__ == '__main__':
    lux = Queue(1)
    cmds = Queue(1)
    bt = BLMThread(cmds, lux)
    bt.start()
    hello = GUI(cmds, lux)
    hello.main()
    cmds.put({'cmd': 'quit'})
    bt.join()

