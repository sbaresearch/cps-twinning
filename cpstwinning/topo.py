#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from cpstwinning.twins import Plc, Hmi

import os


class CpsTwinningTopo(Topo):
    
    def __init__(self, *args, **params):
        self.aml_topo = params.pop('aml_topo', None)
        super(CpsTwinningTopo, self).__init__(*args, **params)
    
    def build(self, **_opts):

        def get_ip(network_config):
            def netmask_to_cidr(netmask):
                # Source: https://stackoverflow.com/a/38085892/8516723
                return str(sum([bin(int(x)).count("1") for x in netmask.split(".")]))
            return network_config['ip']+'/'+netmask_to_cidr(network_config['netmask'])

        if self.aml_topo and self.aml_topo is not None:
            for aml_hmi in self.aml_topo['hmis']:
                network_config = aml_hmi['network']
                self.addHost(
                    aml_hmi['name'],
                    cls=Hmi, 
                    ip=get_ip(network_config), 
                    mac=network_config['mac']
                    ) 
            
            for aml_plc in self.aml_topo['plcs']:
                network_config = aml_plc['network']
                self.addHost(
                    aml_plc['name'], 
                    cls=Plc, 
                    ip=get_ip(network_config), 
                    mac=network_config['mac'], 
                    st_path=aml_plc['st_path'],
                    mb_map=aml_plc['mb_map']
                    ) 
            
            for aml_switch in self.aml_topo['switches']:
                switch = self.addSwitch(aml_switch['name'])
                for link in aml_switch['links']:
                    self.addLink(switch, link)
                    
            attacker = self.addHost('attacker', ip='192.168.0.100')
            self.addLink(switch, attacker)
