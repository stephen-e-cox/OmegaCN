from device_functions import OmegaCN740

instrument = OmegaCN740(slave=3)
temperature, setpoint = instrument.read_temp()
print(temperature)
print(setpoint)

import numpy as np
from traits.api import HasTraits, Str, Int, Float, Enum, Array, Button, Instance
from traitsui.api import View, Item, HGroup, VGroup, spring, Handler
from chaco.api import Plot
from chaco.chaco_plot_editor import ChacoPlotItem
from pyface.timer.api import Timer
from threading import Thread, Event
import os
import datetime
import time
from logging import debug


class Viewer(HasTraits):
    """ This class just contains the two data arrays that will be updated
    by the Controller.  The visualization/editor for this class is a
    Chaco plot.
    """
    index = Array

    data = Array

    plot_type = Enum("line", "scatter")

    view = View(ChacoPlotItem("index", "data",
                              type_trait="plot_type",
                              resizable=True,
                              x_label="Time",
                              y_label="Signal",
                              color="blue",
                              bgcolor="white",
                              border_visible=True,
                              border_width=1,
                              padding_bg_color="lightgray",
                              width=800,
                              height=380,
                              marker_size=2,
                              show_label=False),
                HGroup(spring, Item("plot_type", style='custom'), spring),
                resizable = True,
                buttons = ["OK"],
                width=800, height=500)


class Logger(Thread, HasTraits):

    def __init__(self, sample_name, sample_weight, heating_temp, heating_time):
        super(Logger, self).__init__()

        self.stopRequest = Event()
        self.sample_name = sample_name
        self.sample_weight = sample_weight
        self.heating_temp = heating_temp
        self.heating_time = heating_time
        self.temperature = Float
        self.setpoint = Float
        self.timer = Float
        self.timestamp = datetime.datetime.now()
        self.started = False

        filename = self.sample_name + '.csv'
        header = 'time, temperature, setpoint'
        filesize = 0

        if (os.path.exists(filename) and os.path.isfile(filename)):
            filesize = os.stat(filename).st_size
        self.f = open(filename, 'a')

        if filesize == 0:
            self.f.write('%s\n' % header)

    def run(self):
        start = time.time()
        while not self.stopRequest.isSet():
            time.sleep(0.1)
            self.temperature, self.setpoint = instrument.read_temp()
            self.timestamp = str(datetime.datetime.now())
            self.timer = time.time() - start
            self.started = True
            self.f.write('%s\n' % [self.timestamp, self.timer, self.temperature, self.setpoint])

    def stop(self):
        self.stopRequest.set()
        time.sleep(1)
        try:
            self.f.close()
        except IOError:
            debug('File not open')
            return


class StandaloneRecorder(HasTraits):

    viewer = Instance(Viewer)

    sample_name = Str('default')
    sample_weight = Float
    heating_temp = Float
    heating_time = Int
    plot = Instance(Plot)

    temp_logger = Logger(sample_name=sample_name, sample_weight=sample_weight,
                              heating_temp=heating_temp, heating_time=heating_time)

    view = View(HGroup(VGroup(Item(name='sample_name'),
                              Item(name='sample_weight'),
                              Item(name='heating_temp'),
                              Item(name='heating_time'))), width=1000, height=500, resizable=True,
                title="Temperature Plot")

    def timer_tick(self, *args):

        cur_data = self.viewer.data
        cur_index = self.viewer.index
        if self.temp_logger.started:
            new_data = np.hstack((cur_data, [self.temp_logger.temperature]))
            new_index = np.hstack((cur_index, [self.temp_logger.timer]))
            self.viewer.index = new_index
            self.viewer.data = new_data
            return
        else:
            return


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
    run = Button("Log Temps")
    stop = Button("Stop Logging")
    view = View(Item('controller', style='custom', show_label=False),
                Item(name='run', show_label=False),
                Item(name='stop', show_label=False),
                Item('viewer', style='custom', show_label=False),
                handler=DemoHandler,
                resizable=True)

    def configure_traits(self, *args, **kws):

        return super(Demo, self).configure_traits(*args, **kws)

    def _run_fired(self):

        self.controller.temp_logger.start()
        self.timer = Timer(100, self.controller.timer_tick)

    def _stop_fired(self):

        self.controller.temp_logger.stop()

    def _controller_default(self):
        return StandaloneRecorder(viewer=self.viewer)


popup = Demo()

if __name__ == "__main__":
    popup.configure_traits()
