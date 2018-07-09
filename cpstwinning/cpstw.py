#!/usr/bin/env python

from mininet.node import Controller
from mininet.wifi.net import Mininet_wifi
from mininet.wifi.node import OVSKernelAP
from mininet.log import error
from cpstwinning.topo import CpsTwinningTopo
from cpstwinning.twins import Motor, Plc, Hmi, CandySensor
from cpstwinning.amlparser import AmlParser
from cpstwinning.securitymanager import SecurityManager, RuleTypes
from cpstwinning.replay import Replay
from cpstwinning.replication import Replication
from cpstwinning.statelogging import StateLogging
import os

import logging

logger = logging.getLogger(__name__)
# Set Kafka log level
kafka_logger = logging.getLogger('kafka')
kafka_logger.setLevel(logging.INFO)


class CpsTwinning(Mininet_wifi):

    def __init__(self):
        super(CpsTwinning, self).__init__(controller=Controller, accessPoint=OVSKernelAP)
        self.topo = None
        self.physical_devices = []
        self.security_manager = None
        self.replay = Replay()
        self.replication = None
        self.state_logging = None

    def twinning(self, aml_path):
        """Generates digital twins based on the specification provided via an AML artifact."""
        # Validate path
        if not os.path.isfile(aml_path):
            error("The AML file path '{}' is not valid!\n".format(aml_path))
            return

        if self.topo and self.build:
            error("Topology has already been built!\n")
            return

        # Invoke AML Parser
        parser = AmlParser(aml_path)
        aml_topo = {
            'switches': parser.switches,
            'plcs': parser.plcs,
            'hmis': parser.hmis,
            'aps': parser.aps,
            'mqttbrkrs': parser.mqttbrkrs,
            'rfidrs': parser.rfidrs,
            'iiotgws': parser.iiotgws
        }
        # Create topology
        self.topo = CpsTwinningTopo(aml_topo=aml_topo)
        # Start net
        self.start()

        for motor in parser.motors:
            self.physical_devices.append(
                Motor(
                    motor['name'],
                    motor['vars'],
                    self.get(motor['plc_name']),
                    motor['plc_var_map']
                )
            )
        # Add candy sensor
        self.physical_devices.append(
            CandySensor(
                'CandySensor1',
                self.get('PLC1'),
                {'EXTRACTORRUNNING': 1},
                self.get('RFIDr1')
            )
        )

        security_rules = {}

        for rule_type, rules in parser.security_rules.iteritems():
            if rule_type == RuleTypes().VARCONSTRAINT:
                constraints = []
                for rule in rules:
                    rule['plc'] = self.get(rule['plc_name'])
                    constraints.append(rule)
                security_rules[rule_type] = constraints
            elif rule_type == RuleTypes().VARLINKCONSTRAINT:
                constraints = []
                for rule in rules:
                    side = 'a'
                    for _ in range(2):
                        for key_ab in rule[side]:
                            ab = self.get(key_ab)
                            if isinstance(ab, Plc):
                                rule['plc'] = ab
                                rule['plc_var'] = rule[side][key_ab]
                            elif isinstance(ab, Hmi):
                                rule['hmi'] = ab
                                rule['hmi_var'] = rule[side][key_ab]
                            del rule[side]
                        side = 'b'
                    constraints.append(rule)
                security_rules[rule_type] = constraints

        self.security_manager = SecurityManager(security_rules)

        self.replication = Replication(self)
        self.state_logging = StateLogging(self)

    def start_state_logging(self, print_err=True):
        if not self.__is_topo_built(print_err):
            return
        self.state_logging.start()

    def stop_state_logging(self, print_err=True):
        if not self.__is_topo_built(print_err):
            return
        self.state_logging.stop()

    def start_replication(self, print_err=True):
        if not self.__is_topo_built(print_err):
            return
        self.replication.start()

    def stop_replication(self, print_err=True):
        if not self.__is_topo_built(print_err):
            return
        self.replication.stop()

    def stop(self):
        logger.debug("Terminating CPS Twinning...")
        for pd in self.physical_devices:
            pd.terminate()
        self.stop_replication(False)
        super(CpsTwinning, self).stop()

    def __is_topo_built(self, print_err):
        if not self.topo or not self.build:
            if print_err:
                error("Build topology first!\n")
            return False
        return True
