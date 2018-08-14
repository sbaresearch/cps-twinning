#!/usr/bin/env python
from cpstwinning.constants import STATE_LOG_FILE_LOC, LOG_FORMATTER, LOG_LEVEL
from cpstwinning.utils import setup_logger, UnknownPlcTagException, get_tmp_base_path_from_mkfile
from cpstwinning.twins import Plc, Hmi, Motor
from time import sleep
from errno import ENOENT
from threading import Thread
from multiprocessing.connection import Client
from cpstwinning.plcmessages import TerminateMessage, MonitorMessage, MonitorResponseMessage, GetAllTagNamesMessage, \
    GetAllTagNamesResponseMessage, StopMonitoringMessage
from datetime import datetime

import logging
import os
import socket
import threading
import errno

logger = logging.getLogger(__name__)
state_logger = setup_logger('twin_state', STATE_LOG_FILE_LOC, LOG_FORMATTER, LOG_LEVEL)


class VariableMonitoringThread(Thread):

    def __init__(self, **kwargs):
        Thread.__init__(self)
        # If PLC name is set, we monitor all PLC tags
        self.plc_name = kwargs.get('plc_name', None)
        self.motor = None
        # If no PLC name is set, we check if motor tags should be monitored
        if self.plc_name is None:
            self.motor = kwargs.get('motor', None)
            # No motor supplied, building thread failed. Either PLC name (for monitoring all PLC tags) or motor
            # (for monitoring motor/PLC tags) must be supplied
            if self.motor is None:
                raise ValueError("No PLC name or motor supplied.")
            else:
                self.plc_name = self.motor.plc.name
        self.listener_ready = False
        self.stop_event = threading.Event()

    def __create_connection(self):
        tmp_base = get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.plc_name)
        address = os.path.join(plc_base_path, 'plc_socket')
        # Wait until listener is ready
        # TODO: Refactoring needed (anti-pattern)
        while not self.listener_ready:
            try:
                self.conn = Client(address)
                self.listener_ready = True
            except socket.error as e:
                # Check if listener is not yet ready
                if e.errno == ENOENT:  # socket.error: [Errno 2] No such file or directory
                    sleep(1)
                else:
                    logger.exception("Unknown socket error occurred.")

    def run(self):
        self.__create_connection()
        tag_names = []
        # If motor is none, all PLC tags should be monitored
        if self.motor is None:
            self.conn.send(GetAllTagNamesMessage())
        else:
            tag_names = self.motor.plc_vars_map.keys()
            self.conn.send(MonitorMessage(tag_names))
        while not self.stop_event.is_set():
            try:
                if self.conn.poll():
                    result = self.conn.recv()
                    if isinstance(result, UnknownPlcTagException):
                        raise UnknownPlcTagException(result)
                    elif isinstance(result, TerminateMessage):
                        logger.info("Terminating monitoring of '{}'.".format(', '.join(tag_names)))
                        break
                    elif isinstance(result, GetAllTagNamesResponseMessage):
                        tag_names = result.tag_names
                        # Recreate connection before sending new message
                        self.listener_ready = False
                        self.__create_connection()
                        self.conn.send(MonitorMessage(tag_names))
                    elif isinstance(result, MonitorResponseMessage):
                        # First check if we are currently monitoring a PLC or motor
                        if self.motor is None:
                            dev_name = self.plc_name
                        else:
                            dev_name = self.motor.name
                            # We have to alter the name of the result set, as we are receiving PLC tag
                            # changes, yet we have to transmit the motor tag
                            # The 'plc_vars_map' will contain the mapping: {PLC_TAG_NAME: IDX_MOTOR_VARS}
                            idx_motor_var = self.motor.plc_vars_map.get(result.name)
                            if idx_motor_var is not None:
                                # Set the correct motor tag name
                                result.name = self.motor.vars[idx_motor_var]['name']
                            else:
                                logger.error("Received unknown PLC tag (motor tag map).")
                        if dev_name is not None:
                            state_logger.info("[%s] '%s' variable changed [%s=%s].",
                                              result.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                                              dev_name, result.name, result.value)
                    else:
                        logger.error("Received unexpected message type '%s'.", type(result))
            except EOFError:
                logger.exception("Received EOF.")
                break
            except UnknownPlcTagException:
                logger.exception("Unknown PLC Tag.")

        try:
            # Announce to PLC supervisor that we stop monitoring PLC tags
            logger.info("Announcing PLC supervisor to stop monitoring.")
            self.conn.send(StopMonitoringMessage())
        except IOError, e:
            if e.errno == errno.EPIPE:
                pass
            else:
                logger.exception("Could not announce to PLC supervisor to stop monitoring states for state logging.")

        self.conn.close()
        logger.info("Terminated VariableMonitoringThread.")

    def stop(self):
        logger.info("Stopping VariableMonitoringThread now!")
        self.stop_event.set()


class StateLogging(object):

    def __init__(self, cpstw):
        self.cpstw = cpstw
        self.running = False
        self.mons = []

    def hmi_tag_callback(self, hmi, name, value):
        state_logger.info("[%s] HMI '%s' variable changed [%s=%s].",
                          datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], hmi.name, name, value)

    def __start(self):
        for node in self.cpstw.values():
            if isinstance(node, Plc):
                plc_mon_thread = VariableMonitoringThread(plc_name=node.name)
                plc_mon_thread.start()
                self.mons.append(plc_mon_thread)
            elif isinstance(node, Hmi):
                node.add_var_monitor_clbk(self.hmi_tag_callback)

        for device in self.cpstw.physical_devices:
            if isinstance(device, Motor):
                motor_mon_thread = VariableMonitoringThread(motor=device)
                motor_mon_thread.start()
                self.mons.append(motor_mon_thread)

    def __stop(self):
        for mon in self.mons:
            mon.stop()
        self.mons = []
        for node in self.cpstw.values():
            if isinstance(node, Hmi):
                node.remove_var_monitor_clbk(self.hmi_tag_callback)

    def start(self):
        if not self.running:
            logger.debug("Starting state logging...")
            self.__start()
            self.running = True
        else:
            logger.info("State logging module already started. Nothing to do...")

    def stop(self):
        if self.running:
            logger.debug("Stopping state logging...")
            self.__stop()
            self.running = False
        else:
            logger.info("State logging module already stopped. Nothing to do...")
