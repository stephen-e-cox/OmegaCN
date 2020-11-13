from random import random

import numpy as np
import pandas as pd
from traits.api import HasTraits, Str, Int, Float, Enum, Array, Button, Instance
from traitsui.api import View, Item, HGroup, VGroup, spring, Handler, ArrayEditor
from traitsui.ui_editors.data_frame_editor import DataFrameEditor
from chaco.api import Plot
from chaco.chaco_plot_editor import ChacoPlotItem
from pyface.timer.api import CallbackTimer, do_after
import os
import datetime
import time
import pyfirmata

try:
    from device_functions import OmegaCN740
except ImportError:
    class OmegaCN740:
        def __init__(self, *args, **kw):
            pass

        def read_temp(self):
            return 10 * random(), random()

INSTRUMENT = [OmegaCN740(slave=3), OmegaCN740(slave=4), OmegaCN740(slave=5), OmegaCN740(slave=6)]

arduino_board = pyfirmata.Arduino('/dev/cu.usbmodem145101')
it = pyfirmata.util.Iterator(arduino_board)
it.start()
cell_one_trigger = arduino_board.get_pin('d:4:i')
cell_two_trigger = arduino_board.get_pin('d:5:i')
cell_three_trigger = arduino_board.get_pin('d:6:i')
cell_four_trigger = arduino_board.get_pin('d:7:i')
led = arduino_board.get_pin('d:13:o')
led.write(1)


def random_df():
    return pd.read_csv('testsched.csv')


class TimeTemps(HasTraits):
    data = Instance('pandas.core.frame.DataFrame')

    def _data_default(self):
        return pd.read_csv('testsched.csv')

    # view
    view = View(Item('data', show_label=False, editor=DataFrameEditor(editable=False, show_index=False)),
                width=200, resizable=True)

    # def _timetemp_default(self):
    #     pd.read_csv('testsched.csv')
    #
    # view = View(Item('timetemp', editor=DataFrameEditor(editable=True, show_index=False),
    #                  label='Heating Schedule', resizable=True, show_label=False))


class Viewer(HasTraits):
    """ This class just contains the two data arrays that will be updated
    by the Controller.  The visualization/editor for this class is a
    Chaco plot.
    """
    index = Array

    data = Array

    plot_type = Enum('line', 'scatter')

    view = View(ChacoPlotItem('index', 'data',
                              type_trait='plot_type',
                              resizable=True,
                              x_label='Time',
                              y_label='Signal',
                              color='blue',
                              bgcolor='white',
                              border_visible=True,
                              border_width=1,
                              padding_bg_color='lightgray',
                              width=800,
                              height=380,
                              marker_size=2,
                              show_label=False),
                HGroup(spring, Item('plot_type', style='custom'), spring),
                resizable=True,
                buttons=['OK'],
                width=800, height=500)


class Logger(HasTraits):
    # cell_number = Int
    # step_number = Int
    # heating_temp = Float
    # heating_time = Float

    temperature = Float
    setpoint = Float
    current_time = Float

    start = None
    path = None

    def __init__(self, *args, **kw):
        super(Logger, self).__init__(*args, **kw)

        self.timestamp = datetime.datetime.now().isoformat()

    def set_start_time(self):
        self.start = time.time()

    def update(self):
        self.temperature, self.setpoint = INSTRUMENT[self.cell_number - 1].read_temp()
        self.timestamp = datetime.datetime.now().isoformat()
        self.current_time = time.time() - self.start
        if not self.path:
            self.path = self.make_path()
        self._write()
        print([self.cell_number, self.step_number, self.heating_temp, self.heating_time])

    def make_path(self):
        path = '{}-{}-{}degC-{}min.csv'.format(self.cell_number, self.step_number,
                                               self.heating_temp, self.heating_time)
        i = 1
        while 1:
            if os.path.isfile(path):
                path = '{}-{}-{}degC-{}min-{:03n}.csv'.format(self.cell_number, self.step_number,
                                                              self.heating_temp, self.heating_time, i)
                i += 1
            else:
                return path

    def _write(self):
        with open(self.path, 'a') as wfile:
            args = [self.timestamp, self.current_time, self.temperature, self.setpoint]
            args = [str(a) for a in args]
            line = ','.join(args)
            wfile.write('{}\n'.format(line))


class StandaloneRecorder(HasTraits):
    # viewer = Instance(Viewer)

    cell_number = Int
    step_number = Int
    cell_step_number = Array(np.int, (4, 1))
    heating_temp = Float
    heating_time = Float

    temp_logger = Instance(Logger)

    view = View(HGroup(VGroup(Item(name='cell_number', label="Cell Number"),
                              Item(name='step_number', label="Step Number"),
                              Item(name='heating_temp', label="Heating Temp (C)"),
                              Item(name='heating_time', label="Heating Time (min)"))), width=1000, height=500,
                resizable=True,
                title='Temperature Plot')

    def _temp_logger_default(self):
        return Logger(cell_number=self.cell_number,
                      step_number=self.step_number,
                      heating_temp=self.heating_temp,
                      heating_time=self.heating_time)

    def timer_tick(self, *args):
        self.temp_logger.cell_number = self.cell_number
        self.temp_logger.step_number = self.step_number
        self.temp_logger.heating_temp = self.heating_temp
        self.temp_logger.heating_time = self.heating_time
        if self.temp_logger.current_time > self.heating_time*60:
            self.temp_logger.start = None
        print('tick')
        cur_data = self.viewer.data
        cur_index = self.viewer.index
        if self.temp_logger.start is None:
            self.temp_logger.path = self.temp_logger.make_path()
            self.temp_logger.set_start_time()
            cur_data = []
            cur_index = []
        self.temp_logger.update()

        new_data = np.hstack((cur_data, [self.temp_logger.temperature]))
        new_index = np.hstack((cur_index, [self.temp_logger.current_time]))
        self.viewer.index = new_index
        self.viewer.data = new_data
        if self.temp_logger.current_time > self.heating_time*60:
            self.temp_logger.start = None

class DemoHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """

        info.object.timer.Stop()
        return


class Demo(HasTraits):
    schedule = pd.read_csv('testsched.csv')
    schedule = schedule.values.astype('int64')
    controller = Instance(StandaloneRecorder)
    timetemps = Instance(TimeTemps, ())
    viewer = Instance(Viewer, ())
    timer = Instance(CallbackTimer)
    run = Button('Wait For Signal')
    stop = Button('Stop Waiting')

    view = View(
        HGroup(
            Item('timetemps', style='custom', show_label=False),
            VGroup(
                Item('controller', style='custom', show_label=False),
                Item(name='run', show_label=False),
                Item(name='stop', show_label=False),
                Item('viewer', style='custom', show_label=False))),
        handler=DemoHandler,
        resizable=True)

    def _stop_fired(self):
        self.timer.stop()

    def _run_fired(self):
        self._waiting_loop()
        self.timer = CallbackTimer.timer(callback=self.controller.timer_tick, interval=0.1,
                                         expire=self.controller.heating_time * 60)

    def _controller_default(self):
        return StandaloneRecorder(viewer=self.viewer)

    def _waiting_loop(self):
        while True:
            if cell_one_trigger.read() is True:
                print('triggered--cell one')
                self.controller.cell_number = 1
                self.controller.cell_step_number[0] += 1
                self.controller.step_number = self.controller.cell_step_number[0]
                # self.controller.heating_temp = 300
                # self.controller.heating_time = 15
                time.sleep(1)
                break
            if cell_two_trigger.read() is True:
                print('triggered--cell two')
                self.controller.cell_number = 2
                self.controller.cell_step_number[1] += 1
                self.controller.step_number = self.controller.cell_step_number[1]
                time.sleep(1)
                break
            if cell_three_trigger.read() is True:
                print('triggered--cell three')
                self.controller.cell_number = 3
                self.controller.cell_step_number[2] += 1
                self.controller.step_number = self.controller.cell_step_number[2]
                time.sleep(1)
                break
            if cell_four_trigger.read() is True:
                print('triggered--cell four')
                self.controller.cell_number = 4
                self.controller.cell_step_number[3] += 1
                self.controller.step_number = self.controller.cell_step_number[3][0]
                time.sleep(1)
                break

        # self.controller.step_number = 1
        # self.controller.heating_temp = 300
        # self.controller.heating_time = 15
        self._start_run()

    def _start_run(self):
        schedule = self.timetemps.data
        params = schedule[(schedule.cell == self.controller.cell_number) & (schedule.run == 0)].iloc[0]
        schedule.loc[schedule.index[(schedule.cell == self.controller.cell_number) & (schedule.run == 0)][0], 'run'] = 1
        schedule.to_csv('testsched.csv', index=False)
        # schedule[(schedule.cell == self.controller.cell_number) & (schedule.run == 0)].replace(0, 1, inplace=True)
        try:
            self.controller.heating_temp = params[3]
        except KeyError:
            self.controller.heating_temp = 0
        try:
            self.controller.heating_time = params[2]
        except KeyError:
            self.controller.heating_time = 1
        time.sleep(1)


if __name__ == '__main__':
    popup = Demo()
    popup.configure_traits()
