from random import random

import numpy as np
from traits.api import HasTraits, Str, Int, Float, Enum, Array, Button, Instance
from traitsui.api import View, Item, HGroup, VGroup, spring, Handler
from chaco.api import Plot
from chaco.chaco_plot_editor import ChacoPlotItem
from pyface.timer.api import Timer
import os
import datetime
import time

try:
    from device_functions import OmegaCN740
except ImportError:
    class OmegaCN740:
        def __init__(self, *args, **kw):
            pass

        def read_temp(self):
            return 10*random(), random()


INSTRUMENT = OmegaCN740(slave=3)


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
    sample_name = Str('default')
    sample_weight = Float
    heating_power = Float
    heating_time = Int

    temperature = Float
    setpoint = Float
    current_time = Float

    start = None

    def __init__(self, *args, **kw):
        super(Logger, self).__init__(*args, **kw)

        self.timestamp = datetime.datetime.now().isoformat()

        header = 'datetime,timer,temperature,setpoint'
        self.path = self._make_path()
        with open(self.path, 'w') as wfile:
            wfile.write('{}\n'.format(header))

    def set_start_time(self):
        self.start = time.time()

    def update(self):
        self.temperature, self.setpoint = INSTRUMENT.read_temp()
        self.timestamp = datetime.datetime.now().isoformat()
        self.current_time = time.time() - self.start
        self._write()

    def _make_path(self):
        path = '{}-{}mg-{}%-{}s.csv'.format(self.sample_name, self.sample_weight,
                                            self.heating_power, self.heating_time)
        i = 1
        while 1:
            if os.path.isfile(path):
                path = '{}-{}mg-{}%-{}s-{:03n}.csv'.format(self.sample_name, self.sample_weight,
                                                           self.heating_power, self.heating_time, i)
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
    viewer = Instance(Viewer)

    sample_name = Str('default')
    sample_weight = Float
    heating_power = Float
    heating_time = Int
    plot = Instance(Plot)

    temp_logger = Instance(Logger)

    view = View(HGroup(VGroup(Item(name='sample_name'),
                              Item(name='sample_weight', label="Sample Weight (mg)"),
                              Item(name='heating_power', label="Heating Power (%)"),
                              Item(name='heating_time', label="Heating Time (s)"))), width=1000, height=500, resizable=True,
                title='Temperature Plot')

    def _temp_logger_default(self):
        return Logger(sample_name=self.sample_name,
                      sample_weight=self.sample_weight,
                      heating_power=self.heating_power,
                      heating_time=self.heating_time)

    def timer_tick(self, *args):
        cur_data = self.viewer.data
        cur_index = self.viewer.index
        if self.temp_logger.start is None:
            self.temp_logger.set_start_time()

        self.temp_logger.update()

        new_data = np.hstack((cur_data, [self.temp_logger.temperature]))
        new_index = np.hstack((cur_index, [self.temp_logger.current_time]))
        self.viewer.index = new_index
        self.viewer.data = new_data


class DemoHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """

        info.object.timer.Stop()
        return


class Demo(HasTraits):
    controller = Instance(StandaloneRecorder)
    viewer = Instance(Viewer, ())
    timer = Instance(Timer)
    run = Button('Log Temps')
    stop = Button('Stop Logging')
    view = View(Item('controller', style='custom', show_label=False),
                Item(name='run', show_label=False),
                Item(name='stop', show_label=False),
                Item('viewer', style='custom', show_label=False),
                handler=DemoHandler,
                resizable=True)

    def _stop_fired(self):
        self.timer.stop()

    def _run_fired(self):
        self.timer = Timer(100, self.controller.timer_tick)

    def _controller_default(self):
        return StandaloneRecorder(viewer=self.viewer)


if __name__ == '__main__':
    popup = Demo()
    popup.configure_traits()