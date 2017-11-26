#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
import threading
import time

import smbus

from sibus_lib import BusClient, sibus_init
from sibus_lib.utils import handle_signals

SERVICE_NAME = "sibus.piups"
logger, cfg_data = sibus_init(SERVICE_NAME)


class PiUps(threading.Thread):
    def __init__(self, i2c_bus=0, i2c_address=0x36):
        self.i2c_bus = smbus.SMBus(i2c_bus)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self.i2c_address = i2c_address
        self.charging = False
        self._stopevent = threading.Event()

    def run(self):
        v_old = 0
        while not self._stopevent.isSet():
            v_current = self.voltage()

            delta = v_current - v_old

            if delta > 0:
                print "Charging..."
            else:
                print "Discharging..."

            v_old = v_current
            self._stopevent.wait(5.0)

    def stop(self):
        self._stopevent.set()

    def voltage(self):
        "This function returns as float the voltage from the Raspi UPS Hat via the provided SMBus object"
        address = 0x36
        read = self.i2c_bus.read_word_data(self.i2c_address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 78.125 / 1000000
        return voltage

    def battery_level(self):
        "This function returns as a float the remaining capacity of the battery connected to the Raspi UPS Hat via the provided SMBus object"
        address = 0x36
        read = self.i2c_bus.read_word_data(self.i2c_address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
        return capacity

    def charging(self):
        pass


def get_ups_state():
    logger.info("Voltage: %5.2fV" % piups.voltage())
    logger.info("Battery: %5i%%" % piups.battery_level())


busclient = BusClient(SERVICE_NAME)
busclient.connect(broker="127.0.0.1", port=1883)

piups = PiUps(i2c_bus=1, i2c_address=0x36)
piups.start()

handle_signals()
try:
    while 1:
        if not get_ups_state():
            logger.error("Fail to pulish a message, 30s before retry")
            time.sleep(30)
            busclient.reconnect()
            time.sleep(5)
        else:
            time.sleep(5)
except (KeyboardInterrupt):
    logger.info("Ctrl+C detected !")
except Exception as e:
    logger.exception("Exception in program detected ! \n" + str(e))
finally:
    piups.stop()
    busclient.stop()
