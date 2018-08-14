#!/usr/bin/env python

from threading import Thread, Event
from kafka import KafkaProducer
import time
import serial
import sys
import re
import json

shutdown_event = Event()

# TODO: Parse from specification
ip2devn = {'192.168.0.61': 'RFIDr1'}
kafka_bootstrap_servers = '192.168.56.3:9092'


class RfidSerialLogger(Thread):

    def __init__(self, serial_port, baud_rate):
        Thread.__init__(self)
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        # timeout=0 -> non-blocking mode
        self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=0)
        self.candy_p = re.compile('\[ip=(\S+),candy=(\S+)\]')
        self.kafka_producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers)

    def run(self):
        line = ""
        while not shutdown_event.is_set():
            data = self.ser.read()
            timestamp = int(round(time.time() * 1000))
            sys.stdout.write(data)
            sys.stdout.flush()
            line = line + data
            # Check if line is done
            if "\n" in line:
                candy_log_search = re.search(self.candy_p, line)
                if candy_log_search:
                    ip = candy_log_search.group(1)
                    detected_candy = candy_log_search.group(2)
                    name = ip2devn.get(ip)
                    if name is None:
                        print "Found unknown device with IP %s".format(ip)
                    else:
                        log = {'timestamp': str(timestamp), 'name': name, 'candy': detected_candy}
                        self.__publish_log(log)
                # Reset line
                line = ""
        # Close serial stream and Kafka producer
        self.ser.close()
        self.kafka_producer.close()

    def __publish_log(self, log):
        json_log = json.dumps(log, ensure_ascii=False)
        self.kafka_producer.send('p_logs', key=log['name'], value=json_log)


if __name__ == '__main__':
    print "Starting RFID Serial Logger..."
    nfc_serial_logger = RfidSerialLogger(serial_port='COM4', baud_rate=115200)
    nfc_serial_logger.start()
    try:
        while nfc_serial_logger.is_alive():
            nfc_serial_logger.join(timeout=1.0)
    except (KeyboardInterrupt, SystemExit):
        print "Shutting down RFID serial logger..."
        shutdown_event.set()
        sys.stdout.flush()
