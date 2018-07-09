#!/usr/bin/env python

from mininet.wifi.topo import Topo_WiFi
from mininet.wifi.node import Station, OVSKernelAP
from cpstwinning.twins import Plc, Hmi, RfidReaderMqttWiFi, MqttBroker, GenericServer


class CpsTwinningTopo(Topo_WiFi):

    def __init__(self, *args, **params):
        self.aml_topo = params.pop('aml_topo', None)
        super(CpsTwinningTopo, self).__init__(*args, **params)

    def build(self, **_opts):

        def get_ip(network_config):
            def netmask_to_cidr(netmask):
                # Source: https://stackoverflow.com/a/38085892/8516723
                return str(sum([bin(int(x)).count("1") for x in netmask.split(".")]))

            return network_config['ip'] + '/' + netmask_to_cidr(network_config['netmask'])

        if self.aml_topo and self.aml_topo is not None:
            for aml_hmi in self.aml_topo['hmis']:
                network_config = aml_hmi['network']
                self.addHost(
                    name=aml_hmi['name'],
                    cls=Hmi,
                    ip=get_ip(network_config),
                    mac=network_config['mac']
                )

            for aml_plc in self.aml_topo['plcs']:
                network_config = aml_plc['network']
                self.addHost(
                    name=aml_plc['name'],
                    cls=Plc,
                    ip=get_ip(network_config),
                    mac=network_config['mac'],
                    st_path=aml_plc['st_path'],
                    mb_map=aml_plc['mb_map']
                )

            attacker = self.addHost(name='attacker', ip='192.168.0.100', mac='a2:67:f2:13:1c:06')

            for aml_rfidr in self.aml_topo['rfidrs']:
                network_config = aml_rfidr['network']
                self.addStation(
                    name=aml_rfidr['name'],
                    cls=RfidReaderMqttWiFi,
                    ip=get_ip(network_config),
                    mac=network_config['mac'],
                    mqtt_host=aml_rfidr['host'],
                    mqtt_topic=aml_rfidr['topic'],
                    auth=aml_rfidr['auth']
                )

            for aml_mqttbrkr in self.aml_topo['mqttbrkrs']:
                network_config = aml_mqttbrkr['network']
                self.addHost(
                    name=aml_mqttbrkr['name'],
                    cls=MqttBroker,
                    ip=get_ip(network_config),
                    mac=network_config['mac'],
                    mqtt_conf=aml_mqttbrkr['mqtt_conf']
                )

            for aml_iiotgw in self.aml_topo['iiotgws']:
                network_config = aml_iiotgw['network']
                self.addHost(
                    name=aml_iiotgw['name'],
                    cls=GenericServer,
                    ip=get_ip(network_config),
                    mac=network_config['mac'],
                    cmds=aml_iiotgw['cmds']
                )

            for aml_ap in self.aml_topo['aps']:
                ap = self.addAccessPoint(
                    name=aml_ap['name'],
                    cls=OVSKernelAP,
                    ssid=aml_ap['ssid'],
                    mode=aml_ap['mode'],
                    channel=aml_ap['channel']
                )
                for link in aml_ap['links']:
                    self.addLink(link, ap)

            for aml_switch in self.aml_topo['switches']:
                switch = self.addSwitch(aml_switch['name'])
                for link in aml_switch['links']:
                    self.addLink(switch, link)
                self.addLink(switch, attacker)
