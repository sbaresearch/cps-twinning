#!/usr/bin/env python


class MqttMessage(object):

    def __init__(self):
        pass


class CloseMessage(MqttMessage):

    def __init__(self):
        super(CloseMessage, self).__init__()


class ConnectMessage(MqttMessage):

    def __init__(self, host, port=1883, keepalive=60, bind_address="", auth=None):
        super(MqttMessage, self).__init__()
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.bind_address = bind_address
        self.auth = auth


class PublishMessage(MqttMessage):

    def __init__(self, topic, payload=None, qos=0, retain=False):
        super(MqttMessage, self).__init__()
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class DisconnectMessage(MqttMessage):

    def __init__(self):
        super(DisconnectMessage, self).__init__()
