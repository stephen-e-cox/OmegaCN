import codecs
import serial
import time


class OmegaCN740:

    def __init__(self, slave=1):
        self.slave = bytes(str(hex(slave)[2:].zfill(2)), 'utf-8')
        self.instrument = serial.Serial(port='/dev/tty.usbserial-FT2B7WEI', baudrate=19200, timeout=0.1, parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
        self.instrument.flushInput()
        self.instrument.flushOutput()
        time.sleep(1)

    def read_temp(self):
        temperature, setpoint = self._ask(self._read_temp())
        return temperature, setpoint

    def write_setpoint(self, temperature):
        response = self._ask(self._write_setpoint(10*temperature))
        return response

    def _ask(self, message):
        self.instrument.write(message)
        response = self.instrument.readline()
        message = response[response.index(self.slave + b'03')+4:-4]
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
        return temperature, setpoint

    def _compute_lrc(self, data):

        bytesum = sum(codecs.decode(data, 'hex'))
        checksum = (hex((256 - bytesum) & 0x0ff))[2:]
        return bytes(checksum.zfill(2).upper(), 'utf-8')

    def _read_temp(self):
        message = self.slave + b'03' + b'4700' + b'0002'
        message = b':' + message + self._compute_lrc(message) + b'\r\n'
        return message

    def _write_setpoint(self, temperature):
        message = self.slave + b'06' + b'4701' + bytes(hex(temperature)[2:].zfill(4).upper(), 'utf-8')
        message = b':' + message + self._compute_lrc(message) + b'\r\n'
        return message
