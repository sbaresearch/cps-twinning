#!/usr/bin/env python

from mininet.node import Host
from mininet.wifi.node import Station
from threading import Thread, Event, Lock
from multiprocessing.connection import Client
from cpstwinning.hmimessages import ReadMessage, ReadMessageResult, WriteMessage, SuccessHmiMessage
from cpstwinning.plcmessages import StartMessage, StopMessage, ShowTagsMessage, ShowTagsResponseMessage, \
    TerminateMessage, GetTagMessage, GetTagResponseMessage, SetTagMessage, SetTagResponseMessage, MonitorMessage, \
    MonitorResponseMessage, GetTagsMessage, GetTagsResponseMessage
from cpstwinning.utils import UnknownPlcTagException, NotSupportedPlcTagTypeException, NotSupportedPlcTagClassException
from cpstwinning.mqttmessages import ConnectMessage, PublishMessage, CloseMessage
from time import sleep
from kafka import KafkaProducer
from constants import KAFKA_BOOTSTRAP_SERVERS, KAFKA_V_LOGS_TOPIC

import sys
import os
import utils
import pickle
import logging
import socket
import errno
import json
import time

logger = logging.getLogger(__name__)


class Plc(Host):
    """A PLC host."""

    def config(self, **params):
        super(Plc, self).config(**params)
        # TODO: Error handling
        st_path = params.pop('st_path', None)
        mb_map = params.pop('mb_map', None)
        mb_map_path = self.__persist_mb_map(mb_map) if mb_map is not None else ''
        plc_supervisor_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor.py')
        cmd = '{} {} {} {} {} &'.format(sys.executable, plc_supervisor_path, self.name, st_path, mb_map_path)
        self.cmd(cmd)

    def __persist_mb_map(self, mb_map):
        dir_path = utils.get_dstdir_path_from_mkfile(self.name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        path = os.path.join(dir_path, 'mb_map.txt')
        with open(path, 'wb') as handle:
            pickle.dump(mb_map, handle)
        return path

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.name)
        address = os.path.join(plc_base_path, 'plc_socket')
        self.conn = Client(address)

    def __send(self, msg):
        self.__create_connection()
        self.conn.send(msg)

    def __send_message(self, msg):
        self.__send(msg)
        result = self.conn.recv()
        self.__close()
        if isinstance(result, UnknownPlcTagException):
            raise UnknownPlcTagException(result)
        elif isinstance(result, NotSupportedPlcTagTypeException):
            raise NotSupportedPlcTagTypeException(result)
        elif isinstance(result, NotSupportedPlcTagClassException):
            raise NotSupportedPlcTagClassException(result)
        else:
            return result

    def __close(self):
        self.conn.close()

    def terminate(self):
        logger.debug("Sending Terminate Message to PLC.")
        self.__send(TerminateMessage())
        self.__close()
        super(Plc, self).terminate()

    def start(self):
        return self.__send_message(StartMessage())

    def stop(self):
        return self.__send_message(StopMessage())

    def get_var_value(self, name):
        try:
            result = self.__send_message(GetTagMessage(name))
            if isinstance(result, GetTagResponseMessage):
                return str(result.value) + "\n"
            else:
                logger.error("Unexpected message type: %s.", type(result))
        except UnknownPlcTagException:
            return "ERROR: Variable name '{}' does not exist in PLC.\n".format(name)
        except NotSupportedPlcTagTypeException:
            return "ERROR: The type of variable '{}' is currently not supported.\n".format(name)
        except NotSupportedPlcTagClassException:
            return "ERROR: The class of variable '{}' is currently not supported.\n".format(name)

    def set_var_value(self, name, value):
        try:
            result = self.__send_message(SetTagMessage(name, value))
            if isinstance(result, SetTagResponseMessage):
                return "\n"
            else:
                logger.error("Unexpected message type: %s.", type(result))
        except UnknownPlcTagException:
            return "ERROR: Variable name '{}' does not exist in PLC.\n".format(name)
        except NotSupportedPlcTagTypeException:
            return "ERROR: The type of variable '{}' is currently not supported.\n".format(name)
        except NotSupportedPlcTagClassException:
            return "ERROR: The class of variable '{}' is currently not supported.\n".format(name)

    def show_tags(self):
        result = self.__send_message(ShowTagsMessage())
        if isinstance(result, ShowTagsResponseMessage):
            titles = ["Name", "Class", "Type"]
            # Will contain: { 'name': [...], 'class': [...], 'type': [...] }
            transposed_vars = {}
            for d in result.tags:
                for k, v in d.items():
                    transposed_vars.setdefault(k, []).append(v)
            data = [titles] + list(zip(transposed_vars['name'], transposed_vars['class'], transposed_vars['type']))
            out = ""
            for i, d in enumerate(data):
                out = out + '|'.join(str(x).ljust(30) for x in d) + '\n'
                if i == 0:
                    out = out + '-' * len(out) + '\n'
            return out
        else:
            logger.error("Unexpected message type: %s.", type(result))

    def get_vars(self):
        result = self.__send_message(GetTagsMessage())
        if isinstance(result, GetTagsResponseMessage):
            return result.tags
        else:
            logger.error("Unexpected message type: %s.", type(result))


class Hmi(Host):
    """An HMI host."""

    def config(self, **params):
        super(Hmi, self).config(**params)
        hmi_mb_client_path = os.path.join(utils.get_pkg_path(), 'hmi_mb_client.py')
        self.cmd('{} {} {} &'.format(sys.executable, hmi_mb_client_path, self.name))
        # TODO: Replace with parser vars
        self.vars = [
            {'name': 'StartConveyorBelt', 'mb_table': 'hr', 'mb_addr': 1, 'value': False},
            {'name': 'StopConveyorBelt', 'mb_table': 'hr', 'mb_addr': 2, 'value': False},
            {'name': 'ConveyorVelocity', 'mb_table': 'hr', 'mb_addr': 3, 'value': 0},
            {'name': 'SelectedCandy', 'mb_table': 'hr', 'mb_addr': 4, 'value': 0}
        ]
        self.var_link_clbk = None
        self.__var_monitor_clbks = []

    def set_var_link_clbk(self, clbk):
        self.var_link_clbk = clbk

    def add_var_monitor_clbk(self, clbk):
        self.__var_monitor_clbks.append(clbk)

    def remove_var_monitor_clbk(self, clbk):
        self.__var_monitor_clbks.remove(clbk)

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        hmi_base_path = os.path.join(tmp_base, self.name)
        address = os.path.join(hmi_base_path, 'mb_socket')
        self.conn = Client(address)

    def __send(self, msg):
        self.__create_connection()
        self.conn.send(msg)

    def __close(self):
        self.conn.close()

    def get_var_value(self, name):
        for var in self.vars:
            if var['name'] == name:
                self.__send(ReadMessage('192.168.0.1', var['mb_table'], var['mb_addr']))
                result = self.conn.recv()
                self.__close()
                val_set = False
                if isinstance(result, ReadMessageResult):
                    if type(var['value']) is int:
                        var['value'] = int(result.value)
                    elif type(var['value']) is bool:
                        # Value received via Modbus may be 0/1
                        var['value'] = result.value == 'True' or result.value == '1' or result.value == 1
                    else:
                        raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                    val_set = True
                if not val_set:
                    logger.error('Modbus request timed out.')
                else:
                    if self.var_link_clbk is not None:
                        self.var_link_clbk(var)
                    for clbk in self.__var_monitor_clbks:
                        clbk(self, name, var['value'])
                return str(var['value']) + '\n'
        return "ERROR: Variable name '{}' does not exist in HMI.\n".format(name)

    def set_var_value(self, name, value):
        for var in self.vars:
            if var['name'] == name:
                old_value = var['value']
                # Optimistically set new value in HMI vars
                if type(var['value']) is int:
                    var['value'] = int(value)
                elif type(var['value']) is bool:
                    var['value'] = value == 'True'
                    # Convert boolean
                    value = 1 if var['value'] else 0
                else:
                    raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                logger.info("'{}' value changed {} -> {} in device '{}'.".format(name, old_value, value, self.name))

                self.__send(WriteMessage('192.168.0.1', var['mb_table'], var['mb_addr'], 1, [int(value)]))
                result = self.conn.recv()
                self.__close()
                if not isinstance(result, SuccessHmiMessage):
                    # Error - rollback
                    var['value'] = old_value
                    return 'ERROR: Failed to set value.'

                if self.var_link_clbk is not None:
                    self.var_link_clbk(var)
                for clbk in self.__var_monitor_clbks:
                    clbk(self, name, var['value'])
                return "\n"
        return "ERROR: Variable name '{}' does not exist in HMI.\n".format(name)

    def show_tags(self):
        titles = ["Name"]
        transposed_vars = {}
        for d in self.vars:
            for k, v in d.items():
                transposed_vars.setdefault(k, []).append(v)
        data = [titles] + list(zip(transposed_vars['name']))
        out = ""
        for i, d in enumerate(data):
            out = out + '|'.join(str(x).ljust(30) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        return out

    def get_vars(self):
        return map(lambda x: {'name': x['name'], 'value': x['value']}, self.vars)


class Motor(object):
    """A motor."""

    def __init__(self, name, vars, plc, plc_vars_map):
        self.name = name
        self.plc = plc
        self.vars = vars
        self.plc_vars_map = plc_vars_map  # Name of PLC var to map : Internal motor var
        self.shutdown_event = Event()
        self.motor_thread = PlcMonitorThread(self, plc)
        self.motor_thread.start()

    def get_status(self):
        titles = ["Name", "Value"]
        # Will contain: { 'name': [...], 'value': [...] }
        transposed_vars = {}
        for d in self.vars:
            for k, v in d.items():
                transposed_vars.setdefault(k, []).append(v)
        data = [titles] + list(zip(transposed_vars['name'], transposed_vars['value']))
        out = ""
        for i, d in enumerate(data):
            out = out + '|'.join(str(x).ljust(30) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        return out

    def get_vars(self):
        return self.vars

    def terminate(self):
        self.shutdown_event.set()

    def __str__(self):
        return self.name


class PlcMonitorThread(Thread):

    def __init__(self, dev, plc):
        Thread.__init__(self)
        self.dev = dev
        self.plc = plc
        self.running = False
        self.listener_ready = False

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.plc.name)
        address = os.path.join(plc_base_path, 'plc_socket')
        # Wait until listener is ready
        # TODO: Refactoring needed (anti-pattern)
        while not self.listener_ready:
            try:
                self.conn = Client(address)
                self.listener_ready = True
            except socket.error as e:
                # Check if listener is not yet ready
                if e.errno == errno.ENOENT:  # socket.error: [Errno 2] No such file or directory
                    sleep(1)
                else:
                    logger.exception("Unknown socket error occurred.")

    def __monitor(self):
        self.__create_connection()
        self.conn.send(MonitorMessage(self.dev.plc_vars_map.keys()))

    def __close(self):
        self.conn.close()

    def run(self):
        self.__monitor()
        while not self.dev.shutdown_event.is_set():
            try:
                if self.conn.poll():
                    result = self.conn.recv()
                    if isinstance(result, UnknownPlcTagException):
                        raise UnknownPlcTagException(result)
                    elif isinstance(result, TerminateMessage):
                        logger.info("Terminating monitoring of '{}'.".format(self.dev.name))
                        break
                    elif isinstance(result, MonitorResponseMessage):
                        dev_var_idx = self.dev.plc_vars_map[result.name]
                        var = self.dev.vars[dev_var_idx]['value']
                        if type(var) is int:
                            self.dev.vars[dev_var_idx]['value'] = int(result.value)
                        elif type(var) is bool:
                            self.dev.vars[dev_var_idx]['value'] = result.value
                        else:
                            raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                    else:
                        logger.error("Received unexpected message type '%s'.", type(result))
            except EOFError:
                logger.exception("Received EOF.")
                break
            except UnknownPlcTagException:
                logger.exception("Unknown PLC Tag.")

        self.__close()


class RfidReaderMqttWiFi(Station):
    """A wireless RFID reader."""

    def config(self, **params):
        super(RfidReaderMqttWiFi, self).config(**params)
        self.mqtt_host = params.pop('mqtt_host', None)
        self.mqtt_topic = params.pop('mqtt_topic', None)
        self.auth = params.pop('auth', None)
        if self.mqtt_host is None:
            logger.error("No MQTT host has been provided for station [name=%s].", self.name)
        if self.mqtt_topic is None:
            logger.error("No MQTT topic has been provided for station [name=%s].", self.name)
        mqtt_client_path = os.path.join(utils.get_pkg_path(), 'mqtt_client.py')
        self.cmd('{} {} {} &'.format(sys.executable, mqtt_client_path, self.name))
        self.is_connected = False
        self.read_clbks = []

    def add_read_clbk(self, clbk):
        self.read_clbks.append(clbk)

    def remove_read_clbk(self, clbk):
        self.read_clbks.remove(clbk)

    def read_value(self, value):
        value = value.encode('ascii', 'ignore')
        logger.info("RFID reader [name=%s] read value %s.", self.name, value)
        if not self.is_connected:
            self.__connect_to_mqtt_broker()
            self.is_connected = True
        self.__send(PublishMessage(self.mqtt_topic, value))
        self.__close()
        for clbk in self.read_clbks:
            clbk(value)
        return "\n"

    def terminate(self):
        logger.debug("Sending close message to MQTT client [name=%s].", self.name)
        self.__send(CloseMessage())
        self.is_connected = False
        self.__close()
        super(RfidReaderMqttWiFi, self).terminate()

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        rfidr_base_path = os.path.join(tmp_base, self.name)
        address = os.path.join(rfidr_base_path, 'mqtt_socket')
        self.conn = Client(address)

    def __connect_to_mqtt_broker(self):
        conn_msg = ConnectMessage(self.mqtt_host, auth=self.auth)
        self.__send(conn_msg)
        self.__close()

    def __send(self, msg):
        self.__create_connection()
        self.conn.send(msg)

    def __close(self):
        self.conn.close()


class MqttBroker(Host):
    """A MQTT broker."""

    def config(self, **params):
        super(MqttBroker, self).config(**params)
        mqtt_conf = params.pop('mqtt_conf', None)
        if mqtt_conf is None:
            logger.error("Could not start MQTT broker [name=%s], because no path to config file has been provided.",
                         self.name)
        else:
            self.cmd('mosquitto -c {} &'.format(mqtt_conf))

    def terminate(self):
        self.cmd('pkill -f mosquitto')
        super(MqttBroker, self).terminate()


class GenericServer(Host):
    """A generic server."""

    def config(self, **params):
        super(GenericServer, self).config(**params)
        cmds = params.pop('cmds', None)
        if cmds is None:
            logger.error("Could not start generic server [name=%s], because no command has been provided.",
                         self.name)
        else:
            for cmd in cmds:
                self.cmd(cmd)


class CandySensor(object):
    """A candy sensor."""

    def __init__(self, name, plc, plc_vars_map, rfidr):
        self.name = name
        self.plc = plc
        self.plc_vars_map = plc_vars_map  # Name of PLC var to map : Internal candy sensor var
        self.rfidr = rfidr
        self.vars = [{'name': 'Candy', 'value': None}, {'name': 'ExtractorRunning', 'value': False}]
        self.shutdown_event = Event()
        self.vars_mutex = Lock()
        self.plc_monitor_thread = PlcMonitorThread(self, plc)
        self.plc_monitor_thread.start()
        self.candy_sensor_vars_thread = self.CandySensorVarsThread(self)
        self.candy_sensor_vars_thread.start()
        # Add callback method in RFID reader twin
        self.rfidr.add_read_clbk(self.rfidr_clbk)

    def rfidr_clbk(self, value):
        with self.vars_mutex:
            candy_filter = filter(lambda n: n.get('name') == 'Candy', self.vars)
            if len(candy_filter):
                candy_idx = self.vars.index(candy_filter[0])
                self.vars[candy_idx]['value'] = value
            else:
                logger.error('Could not find variable [name=Candy] in candy sensor [name=%s].', self.name)

    def __str__(self):
        return self.name

    def terminate(self):
        self.rfidr.remove_read_clbk(self.rfidr_clbk)
        self.shutdown_event.set()

    class CandySensorVarsThread(Thread):

        def __init__(self, candy_sensor):
            Thread.__init__(self)
            self.candy_sensor = candy_sensor
            self.kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

        def run(self):
            # Remember when extractor started
            extractor_active = False
            while not self.candy_sensor.shutdown_event.is_set():
                with self.candy_sensor.vars_mutex:
                    extractor_running_filter = filter(lambda n: n.get('name') == 'ExtractorRunning',
                                                      self.candy_sensor.vars)
                    candy_filter = filter(lambda n: n.get('name') == 'Candy', self.candy_sensor.vars)
                    if len(extractor_running_filter) and len(candy_filter):
                        extractor_start_idx = self.candy_sensor.vars.index(extractor_running_filter[0])
                        extractor_start = self.candy_sensor.vars[extractor_start_idx]['value']
                        candy_idx = self.candy_sensor.vars.index(candy_filter[0])
                        candy = self.candy_sensor.vars[candy_idx]['value']
                        if extractor_start:
                            extractor_active = True
                        else:
                            if extractor_active:
                                # Extractor is done
                                if candy is not None:
                                    # TODO: Adapt sleep to real sensor latency
                                    sleep(2)
                                    logger.info('Candy sensor [name=%s] detected candy [value=%s].',
                                                self.candy_sensor.name, candy)
                                    self._publish_candy_detected(candy)
                                else:
                                    logger.warn(
                                        'Extractor is done, but no candy has been detected by RFID reader beforehand!')
                            # Extractor is done, reset:
                            extractor_active = False
                    else:
                        logger.error(
                            'Could not find variables [name=ExtractorRunning,name=Candy] in candy sensor [name=%s].',
                            self.candy_sensor.name)
            self.kafka_producer.close()

        def _publish_candy_detected(self, candy):
            timestamp = int(round(time.time() * 1000))
            log = {'timestamp': str(timestamp), 'name': self.candy_sensor.name, 'candy': candy}
            json_log = json.dumps(log, ensure_ascii=False)
            self.kafka_producer.send(KAFKA_V_LOGS_TOPIC, key=log['name'], value=json_log)
