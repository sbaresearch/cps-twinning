#!/usr/bin/env python

from cpstwinning.constants import LOG_FILE_LOC, LOG_LEVEL
from cpstwinning.mqttmessages import ConnectMessage, PublishMessage, DisconnectMessage, CloseMessage
from multiprocessing.connection import Listener

import paho.mqtt.client as mqtt
import sys
import logging
import utils
import os

# Logging
logging.basicConfig(filename=LOG_FILE_LOC, level=LOG_LEVEL)
logger = logging.getLogger('mqtt_client')


class MqttClient(object):

    def __init__(self, name):
        self.name = name
        self.is_connected = False
        self.__init_listener()

    def __init_listener(self):
        def on_connect(client, userdata, flags, rc):
            logger.info("MQTT client [name=%s] connected with result code %s.", self.name, str(rc))
            self.is_connected = True

        def disconnect():
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False

        # Create MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        dev_base_path = os.path.join(tmp_base, self.name)
        # Create device base path if it does not exist
        if not os.path.exists(dev_base_path):
            os.makedirs(dev_base_path)
        address = os.path.join(dev_base_path, 'mqtt_socket')
        # Ensure that socket does not exist
        try:
            os.unlink(address)
        except OSError:
            if os.path.exists(address):
                logger.exception('Could not remove socket file.')
        # Create listener
        listener = Listener(address)
        while True:
            conn = listener.accept()
            msg = conn.recv()
            if isinstance(msg, ConnectMessage):
                if msg.auth is not None:
                    username = msg.auth['username']
                    password = msg.auth['password']
                    if username is None:
                        logger.error(
                            "Could not authenticate MQTT client [name=%s], " +
                            "because username has no username has been provided.",
                            self.name
                        )
                    else:
                        self.client.username_pw_set(username, password=password)
                self.client.connect(msg.host, msg.port, msg.keepalive, msg.bind_address)
                self.client.loop_start()
            elif isinstance(msg, PublishMessage):
                self.client.publish(msg.topic, msg.payload, msg.qos, msg.retain)
            elif isinstance(msg, DisconnectMessage):
                disconnect()
            elif isinstance(msg, CloseMessage):
                disconnect()
                conn.close()
                break
        listener.close()


def main():
    if len(sys.argv) != 2:
        raise RuntimeError('Wrong number of arguments. Usage: python mqtt_client.py <name>')
    MqttClient(sys.argv[1])


if __name__ == '__main__':
    main()
