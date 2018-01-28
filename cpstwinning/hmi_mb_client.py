#!/usr/bin/env python

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse

import argparse
import sys
import logging

UNIT = 0x01
TIMEOUT = 100
# Logging
logging.basicConfig(filename='/tmp/cps-twinning.log', level=logging.DEBUG)

class HmiMbClient(object):
    
    def __init__(self):
        self.parse_args()
        
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("ip", help="display a tag's value")
        parser.add_argument("--read", nargs='+', help="read a tag's value")
        parser.add_argument("--write", nargs='+', help="write a tag's value")

        args = parser.parse_args()
        mb_tbls = {
            'co': {'read': self.read_coils, 'write': self.write_coils},
            'di': {'read': self.read_discrete_inputs},
            'hr': {'read': self.read_holding_registers, 'write': self.write_registers},
            'ir': {'read':  self.read_input_registers}
            }
        # TODO: Implement proper validation
        if args.ip and args.read and len(args.read) == 2:
            if args.read[0] in mb_tbls:
                mb_tbls[args.read[0]]['read'](args.ip, int(args.read[1]))
            else:
                self.__output("Invalid Modbus table mode, use 'co', 'di', 'hr' or 'ir'.")
        elif args.ip and args.write and len(args.write) == 2:
            if args.write[0] in mb_tbls:
                mthd = mb_tbls.get(args.write[0]).get('write')
                if mthd is not None:
                    addr, v = list(map(lambda x: int(x), args.write[1].split('=')))
                    mthd(args.ip, addr, v)
                else:
                    self.__output("Cannot perform action, invalid Modbus table mode.")
            else:
                self.__output("Invalid Modbus table mode, use 'co', 'di', 'hr' or 'ir'.")
        else:
            self.__output('Invalid args.')

    def read_coils(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_coils(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadCoilsResponse) and len(result.bits):
                self.__output(result.bits[0])

    def read_holding_registers(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_holding_registers(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadHoldingRegistersResponse) and len(result.registers):
                self.__output(result.registers[0])

    def read_input_registers(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_input_registers(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadInputRegistersResponse) and len(result.registers):
                self.__output(result.registers[0])
        
    def read_discrete_inputs(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_discrete_inputs(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadDiscreteInputsResponse) and len(result.bits):
                self.__output(result.bits[0])

    def write_coils(self, ip, address, value):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.write_coils(address - 1, [value], unit=UNIT)
        
    def write_registers(self, ip, address, value):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.write_registers(address - 1, [value], unit=UNIT)

    def __output(self, out, flush=True):
        print out
        if flush:
            sys.stdout.flush()
            

def main():
    HmiMbClient()


if __name__ == '__main__':
    main()
