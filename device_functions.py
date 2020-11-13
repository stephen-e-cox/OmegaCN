import codecs
import serial
import time
import numpy as np


class OmegaCN740:

    def __init__(self, slave=1, port='/dev/tty.usbserial-FT2B7WEI'):
        self.slave = '{:02x}'.format(slave)
        self.port = port
        self.instrument = serial.Serial(port=self.port, baudrate=19200, timeout=0.1, parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
        self.instrument.flushInput()
        self.instrument.flushOutput()
        time.sleep(0.1)

    def read_temp(self):
        temperature, setpoint = self._ask(self._read_temp())
        return temperature, setpoint

    def write_setpoint(self, temperature):
        response = self._ask(self._write_setpoint(10*temperature))
        return response

    def _ask(self, message):
        self.instrument.write(message)
        # response = self.instrument.readline().decode('utf-8')
        # message = response[response.index('{}{}'.format(self.slave, '03'))+4:-4]
        # message_length = int(message[0:2])
        # if message_length == 4:
        #     temperature = message[2:6]
        #     temperature = int(temperature, 16)/10
        #     setpoint = message[6:10]
        #     setpoint = int(setpoint, 16)/10
        # if message_length == 2:
        #     temperature = message[2:6]
        #     temperature = int(temperature, 16)
        #     setpoint = None
        try:
            response = self.instrument.readline().decode('utf-8')
            message = response[response.index('{}{}'.format(self.slave, '03'))+4:-4]
            message_length = int(message[0:2])
            if message_length == 4:
                temperature = message[2:6]
                temperature = int(temperature, 16)/10
                setpoint = message[6:10]
                setpoint = int(setpoint, 16)/10
            if message_length == 2:
                temperature = message[2:6]
                temperature = int(temperature, 16)
                setpoint = None
        except ValueError:
            temperature = np.nan
            setpoint = np.nan
        return temperature, setpoint

    def _compute_lrc(self, data):
        bytesum = sum(codecs.decode(data, 'hex'))
        checksum = (hex((256 - bytesum) & 0x0ff))[2:]
        return checksum.zfill(2).upper()

    def _read_temp(self):
        data = '0002'

        # message = b''.join([self.slave, b'03', b'4700', b'0002'])
        # message = b''.join([b':', message, self._compute_lrc(message), b'\r\n'])
        message = self._message('read', '4700', data)
        return message

    def _write_setpoint(self, temperature):
        data = hex(temperature)[2:].zfill(4).upper()
        data = '{:04x}'.format(temperature).upper()

        # message = b''.join([self.slave, b'06', b'4701', bytes(hex(temperature)[2:].zfill(4).upper(), 'utf-8')])
        # message = b''.join([b':', message, self._compute_lrc(message), b'\r\n'])
        message = self._message('write', '4701', data)
        return message

    def _message(self, rw, reg, data):
        if rw == 'write':
            rw = '06'
        else:
            rw = '03'
        message = '{}{}{}{}'.format(self.slave, rw, reg, data)
        message = bytes('{}{}{}{}'.format(':', message, self._compute_lrc(message), '\r\n'), 'utf-8')
        return message
