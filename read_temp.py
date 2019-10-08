from device_functions import OmegaCN740

instrument = OmegaCN740()
temperature, setpoint = instrument.read_temp()
print(temperature)
print(setpoint)

from traits.api import HasTraits, Str, Int, Float, Button, Instance
from traitsui.api import View, Item, HGroup, VGroup
from chaco.api import Plot, ArrayPlotData
from enable.api import ComponentEditor
from threading import Thread, Event
import os
import datetime
import time
from logging import debug


class Logger(Thread):

    def __init__(self, sample_name, sample_weight, heating_temp, heating_time):
        super(Logger, self).__init__()

        self.stopRequest = Event()

        self.sample_name = sample_name
        self.sample_weight = sample_weight
        self.heating_temp = heating_temp
        self.heating_time = heating_time

        filename = self.sample_name + '.csv'
        header = 'time, temperature, setpoint'
        filesize = 0

        if (os.path.exists(filename) and os.path.isfile(filename)):
            filesize = os.stat(filename).st_size
        self.f = open(filename, 'a')

        if filesize == 0:
            self.f.write('%s\n' % header)

    def run(self):

        while not self.stopRequest.isSet():
            temperature, setpoint = instrument.read_temp()
            time = str(datetime.datetime.now())
            print(temperature)
            print(setpoint)
            self.f.write('%s\n' % [time, temperature, setpoint])

    def stop(self):
        self.stopRequest.set()
        time.sleep(1)
        try:
            self.f.close()
        except IOError:
            debug('File not open')
            return

class StandaloneRecorder(HasTraits):

    sample_name = Str
    sample_weight = Float
    heating_temp = Float
    heating_time = Int
    plot = Instance(Plot)
    run = Button("Log Temps")
    stop = Button("Stop Logging")

    sample_name = 'default'

    def _plot_default(self):
        times = []
        temps = []
        plotdata = ArrayPlotData(x=times, y=temps)

        plot = Plot(plotdata)
        plot.plot(("x", "y"), type="line", color="blue")
        plot.title = "Temperature History"
        return plot

    def _run_fired(self):

        self.temp_logger = Logger(sample_name=self.sample_name, sample_weight=self.sample_weight,
                                  heating_temp=self.heating_temp, heating_time=self.heating_time)
        self.temp_logger.start()

    def _stop_fired(self):
        self.temp_logger.stop()


view1 = View(HGroup(VGroup(Item(name='sample_name'),
             Item(name='sample_weight'),
             Item(name='heating_temp'),
             Item(name='heating_time'),
             Item(name='run'),
             Item(name='stop')),
             Item('plot', editor=ComponentEditor(),
                  show_label=False)), width=1000, height=500, resizable=True, title="Temperature Plot")

temprec = StandaloneRecorder()
temprec.configure_traits(view=view1)