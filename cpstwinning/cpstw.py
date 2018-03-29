#!/usr/bin/env python

from mininet.net import Mininet
from mininet.log import error
from cpstwinning.topo import CpsTwinningTopo
from cpstwinning.twins import Motor, Plc, Hmi
from cpstwinning.amlparser import AmlParser
from cpstwinning.securitymanager import SecurityManager, RuleTypes
import os

import logging

logger = logging.getLogger(__name__)


class CpsTwinning(Mininet):

    def __init__(self):
        super(CpsTwinning, self).__init__()
        self.topo = None
        self.physical_devices = []
        self.security_manager = None

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
        aml_topo = {'switches': parser.switches, 'plcs': parser.plcs, 'hmis': parser.hmis}
        self.topo = CpsTwinningTopo(aml_topo=aml_topo)
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

    def stop(self):
        logger.debug("Terminating CPS Twinning...")
        super(CpsTwinning, self).stop()
