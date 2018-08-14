#!/usr/bin/env python

from kafka import KafkaProducer
import time
import json

kafka_bootstrap_servers = '192.168.56.3:9092'


class RfidStimuliPusher(object):

    def __init__(self):
        self.kafka_producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers)

    def run(self):
        timestamp = int(round(time.time() * 1000))
        log = {'timestamp': str(timestamp), 'name': 'RFIDr1', 'candy': 'Mint'}
        self.__publish_log(log)
        self.kafka_producer.close()

    def __publish_log(self, log):
        json_log = json.dumps(log, ensure_ascii=False)
        self.kafka_producer.send('p_logs', key=log['name'], value=json_log)


if __name__ == '__main__':
    rfid_stimuli_pusher = RfidStimuliPusher()
    rfid_stimuli_pusher.run()
