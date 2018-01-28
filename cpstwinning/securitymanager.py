#!/usr/bin/env python

from mininet.util import pmonitor
from mininet.node import Host
from mininet.log import error
from threading import Event, Thread

import os
import utils
import sys
import logging

# Logging
logging.basicConfig(filename='/tmp/cps-twinning.log', level=logging.DEBUG)


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
        self._plc_supervisor_client_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor_client.py')
        self.rule = rule
    
    def __get_base_supervisor_client_cmd(self):
        return '{} {}'.format(sys.executable, self._plc_supervisor_client_path)
    
    def run(self):
        popens = {}
        popens[ "plc" ] = self.rule['plc'].popen('{} --monitor {}'.format(self.__get_base_supervisor_client_cmd(), self.rule['var_name']))
        for host, line in pmonitor(popens):
            if host:
                l = line.strip()
                spl_l = l.split(',')
                if len(spl_l) != 2:
                    logging.error("ERROR. Received unknown line {}.\n".format(l))
                else:
                    name, val = spl_l
                    if self.rule['predicate'] == Predicates.MAXVAL:
                        if int(val) > self.rule['value']:
                            logging.warning("WARNING! {} exceeded max value of {} ({}).".format(self.rule['var_name'], self.rule['value'], val))

                            
class VariableLinkPlcMonitoringThread(Thread):
    
    def __init__(self, rule):
        Thread.__init__(self)
        self._plc_supervisor_client_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor_client.py')
        self.rule = rule
    
    def __get_base_supervisor_client_cmd(self):
        return '{} {}'.format(sys.executable, self._plc_supervisor_client_path)
    
    def run(self):
        popens = {}
        popens[ "plc" ] = self.rule['plc'].popen('{} --monitor {}'.format(self.__get_base_supervisor_client_cmd(), self.rule['plc_var']))
        for host, line in pmonitor(popens):
            if host:
                l = line.strip()
                spl_l = l.split(',')
                if len(spl_l) != 2:
                    logging.error("ERROR. Received unknown line {}.\n".format(l))
                else:
                    name, val = spl_l
                    if self.rule['predicate'] == Predicates.EQUALS:
                        for var in self.rule['hmi'].vars:
                            warn = False
                            if var['name'] == self.rule['hmi_var']:
                                if type(var['value']) is int:
                                   if var['value'] != int(val):
                                       warn = True
                                elif type(var['value']) is bool:
                                    if var['value'] != (val == 'True'):
                                        warn = True
                                if warn:
                                    logging.warning("WARNING! HMI variable '{}' does not equal PLC variable '{}'.".format(var['value'], val))


class VariableLinkHmiMonitoringThread(Thread):
    
    def __init__(self, rule):
        Thread.__init__(self)
        self._plc_supervisor_client_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor_client.py')
        self.rule = rule
    
    def __get_base_supervisor_client_cmd(self):
        return '{} {}'.format(sys.executable, self._plc_supervisor_client_path)
    
    def run(self):
        popens = {}
        # TODO: FIX UPPER
        popens[ "plc" ] = self.rule['plc'].popen('{} --get {}'.format(self.__get_base_supervisor_client_cmd(), self.rule['plc_var'].upper()))
        for host, line in pmonitor(popens):
            val = line.rstrip()
            if host and val:
                if self.rule['predicate'] == Predicates.EQUALS:
                    for var in self.rule['hmi'].vars:
                        warn = False
                        if var['name'] == self.rule['hmi_var']:
                            if type(var['value']) is int:
                               if var['value'] != int(val):
                                   warn = True
                            elif type(var['value']) is bool:
                                if var['value'] != (val == 'True'):
                                    warn = True
                            if warn:
                                logging.warning("WARNING! HMI variable '{}' does not equal PLC variable '{}'.".format(var['value'], val))
