#!/usr/bin/env python

from mininet.node import Host
from mininet.log import error
from threading import Thread
from multiprocessing.connection import Client
from cpstwinning.plcmessages import TerminateMessage, MonitorMessage, MonitorResponseMessage, GetTagMessage, \
    GetTagResponseMessage
from cpstwinning.utils import UnknownPlcTagException
from time import sleep
from errno import ENOENT

import os
import utils
import logging
import socket

logger = logging.getLogger(__name__)


class RuleTypes(object):
    VARCONSTRAINT = 0x01
    VARLINKCONSTRAINT = 0x02

    def __setattr__(self, *_):
        pass


class Predicates(object):
    MAXVAL = "RequiredMaxValue"
    EQUALS = "equals"

    def __setattr__(self, *_):
        pass


class SecurityManager(object):

    def __init__(self, security_rules):
        self.rules = security_rules
        for rule_type, rules in security_rules.iteritems():
            if rule_type == RuleTypes().VARCONSTRAINT:
                for rule in rules:
                    var_monitoring_thread = VariableMonitoringThread(rule)
                    var_monitoring_thread.start()
            elif rule_type == RuleTypes().VARLINKCONSTRAINT:
                for rule in rules:
                    var_link_plc_monitoring_thread = VariableLinkPlcMonitoringThread(rule)
                    var_link_plc_monitoring_thread.start()
                    rule['hmi'].set_var_link_clbk(self.check_var_link_get_set_hmi_var)

    def check_var_link_get_set_hmi_var(self, var):
        for rule_type, rules in self.rules.iteritems():
            if rule_type == RuleTypes().VARLINKCONSTRAINT:
                for rule in rules:
                    if rule['hmi_var'] == var['name']:
                        var_link_hmi_monitoring_thread = VariableLinkHmiMonitoringThread(rule)
                        var_link_hmi_monitoring_thread.start()


class VariableMonitoringThread(Thread):

    def __init__(self, rule):
        Thread.__init__(self)
        self.rule = rule
        self.listener_ready = False

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.rule['plc'].name)
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
        tag_names = [self.rule['var_name']]
        self.conn.send(MonitorMessage(tag_names))
        while True:
            try:
                if self.conn.poll():
                    result = self.conn.recv()
                    if isinstance(result, UnknownPlcTagException):
                        raise UnknownPlcTagException(result)
                    elif isinstance(result, TerminateMessage):
                        logger.info("Terminating monitoring of '{}'.".format(self.rule['var_name']))
                        break
                    elif isinstance(result, MonitorResponseMessage):
                        if self.rule['predicate'] == Predicates.MAXVAL:
                            if int(result.value) > self.rule['value']:
                                logger.warning("ALERT! '{}' tag [{}={}] exceeds max value of {}."
                                               .format(self.rule['plc'].name, self.rule['var_name'], result.value,
                                                       self.rule['value']))
                    else:
                        logger.error("Received unexpected message type '%s'.", type(result))
            except EOFError:
                logger.exception("Received EOF.")
                break
            except UnknownPlcTagException:
                logger.exception("Unknown PLC Tag.")

        self.conn.close()


class VariableLinkPlcMonitoringThread(Thread):

    def __init__(self, rule):
        Thread.__init__(self)
        self.rule = rule
        self.listener_ready = False

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.rule['plc'].name)
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
        tag_names = [self.rule['plc_var']]
        self.conn.send(MonitorMessage(tag_names))
        while True:
            try:
                result = self.conn.recv()
                if isinstance(result, UnknownPlcTagException):
                    raise UnknownPlcTagException(result)
                elif isinstance(result, TerminateMessage):
                    logger.info("Terminating monitoring of '{}'.".format(self.rule['plc_var']))
                    break
                elif isinstance(result, MonitorResponseMessage):
                    if self.rule['predicate'] == Predicates.EQUALS:
                        for var in self.rule['hmi'].vars:
                            warn = False
                            if var['name'] == self.rule['hmi_var']:
                                if type(var['value']) is int:
                                    if var['value'] != int(result.value):
                                        warn = True
                                elif type(var['value']) is bool:
                                    if var['value'] != (result.value == 'True'):
                                        warn = True
                                if warn:
                                    logger.warning("ALERT! '{}' tag [{}={}] does not equal '{}' tag [{}={}]."
                                                   .format(self.rule['hmi'].name, var['name'], var['value'],
                                                           self.rule['plc'].name, self.rule['plc_var'], result.value))
                else:
                    logger.error("Received unexpected message type '%s'.", type(result))
            except EOFError:
                logger.exception("Received EOF.")
                break
            except UnknownPlcTagException:
                logger.exception("Unknown PLC Tag.")

        self.conn.close()


class VariableLinkHmiMonitoringThread(Thread):

    def __init__(self, rule):
        Thread.__init__(self)
        self.rule = rule
        self.listener_ready = False

    def __create_connection(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        plc_base_path = os.path.join(tmp_base, self.rule['plc'].name)
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
        # TODO: FIX UPPER
        self.conn.send(GetTagMessage(self.rule['plc_var'].upper()))
        try:
            result = self.conn.recv()
            if isinstance(result, UnknownPlcTagException):
                raise UnknownPlcTagException(result)
            elif isinstance(result, GetTagResponseMessage):
                if self.rule['predicate'] == Predicates.EQUALS:
                    for var in self.rule['hmi'].vars:
                        warn = False
                        if var['name'] == self.rule['hmi_var']:
                            if type(var['value']) is int:
                                if var['value'] != int(result.value):
                                    warn = True
                            elif type(var['value']) is bool:
                                if var['value'] != (result.value == 'True'):
                                    warn = True
                            if warn:
                                logger.warning("ALERT! '{}' tag [{}={}] does not equal '{}' tag [{}={}]."
                                               .format(self.rule['hmi'].name, var['name'], var['value'],
                                                       self.rule['plc'].name, self.rule['plc_var'], result.value))
            else:
                logger.error("Received unexpected message type '%s'.", type(result))
        except EOFError:
            logger.exception("Received EOF.")
        except UnknownPlcTagException:
            logger.exception("Unknown PLC Tag.")

        self.conn.close()
