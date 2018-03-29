#!/usr/bin/env python

from mininet.node import Host
from threading import Thread
from multiprocessing.connection import Client
from cpstwinning.hmimessages import ReadMessage, ReadMessageResult, WriteMessage, SuccessHmiMessage
from cpstwinning.plcmessages import StartMessage, StopMessage, ShowTagsMessage, ShowTagsResponseMessage, \
    TerminateMessage, GetTagMessage, GetTagResponseMessage, SetTagMessage, SetTagResponseMessage, MonitorMessage, \
    MonitorResponseMessage, GetTagsMessage, GetTagsResponseMessage
from cpstwinning.utils import UnknownPlcTagException
from time import sleep

import sys
import os
import utils
import pickle
import logging
import socket
import errno

logger = logging.getLogger(__name__)


# TODO: Remove PLC Supervisor Client and implement UDS
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
        try:
            result = self.conn.recv()
            self.__close()
            if isinstance(result, UnknownPlcTagException):
                raise UnknownPlcTagException(result)
            else:
                return result
        except UnknownPlcTagException:
            if isinstance(msg, GetTagMessage) or isinstance(msg, SetTagMessage):
                return "ERROR: Variable name '{}' does not exist in PLC.\n".format(msg.name)
            else:
                logger.exception("Unknown PLC Tag.")

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
        result = self.__send_message(GetTagMessage(name))
        if isinstance(result, GetTagResponseMessage):
            return str(result.value) + "\n"
        else:
            logger.error("Unexpected message type: %s.", type(result))

    def set_var_value(self, name, value):
        result = self.__send_message(SetTagMessage(name, value))
        if isinstance(result, SetTagResponseMessage):
            return "\n"
        else:
            logger.error("Unexpected message type: %s.", type(result))

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
                out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
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
        self.vars = [{'name': 'Start', 'mb_table': 'hr', 'mb_addr': 1, 'value': False},
                     {'name': 'Stop', 'mb_table': 'hr', 'mb_addr': 2, 'value': False},
                     {'name': 'Velocity', 'mb_table': 'hr', 'mb_addr': 3, 'value': 0}]
        self.var_link_clbk = None
        self.__var_monitor_clbk = None

    def set_var_link_clbk(self, clbk):
        self.var_link_clbk = clbk

    def set_var_monitor_clbk(self, clbk):
        self.__var_monitor_clbk = clbk

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
                    if self.__var_monitor_clbk is not None:
                        self.__var_monitor_clbk(self, name, var['value'])
                return str(var['value']) + '\n'
        self.__close()
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
                if not isinstance(result, SuccessHmiMessage):
                    # Error - rollback
                    var['value'] = old_value
                    return 'ERROR: Failed to set value.'

                if self.var_link_clbk is not None:
                    self.var_link_clbk(var)
                if self.__var_monitor_clbk is not None:
                    self.__var_monitor_clbk(self, name, var['value'])
        self.__close()
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
            out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
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
        self.motor_thread = MotorMonitorThread(self, plc)
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
            out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        return out

    def get_vars(self):
        return self.vars

    def __str__(self):
        return self.name


class MotorMonitorThread(Thread):

    def __init__(self, motor, plc):
        Thread.__init__(self)
        self.motor = motor
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
        self.conn.send(MonitorMessage(self.motor.plc_vars_map.keys()))

    def __close(self):
        self.conn.close()

    def run(self):
        self.__monitor()
        self.running = True
        while self.running:
            try:
                result = self.conn.recv()
                if isinstance(result, UnknownPlcTagException):
                    raise UnknownPlcTagException(result)
                elif isinstance(result, TerminateMessage):
                    self.running = False
                    logger.info("Terminating monitoring of '{}'.".format(self.motor.name))
                elif isinstance(result, MonitorResponseMessage):
                    motor_var_idx = self.motor.plc_vars_map[result.name]
                    var = self.motor.vars[motor_var_idx]['value']
                    if type(var) is int:
                        self.motor.vars[motor_var_idx]['value'] = int(result.value)
                    elif type(var) is bool:
                        self.motor.vars[motor_var_idx]['value'] = result.value
                    else:
                        raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                else:
                    logger.error("Received unexpected message type '%s'.", type(result))
            except EOFError:
                logger.exception("Received EOF.")
                self.running = False
            except UnknownPlcTagException:
                logger.exception("Unknown PLC Tag.")

        self.__close()
