#!/usr/bin/env python

from cpstwinning.constants import LOG_FILE_LOC, LOG_LEVEL
from cpstwinning.utils import ModbusTables
from multiprocessing.connection import Listener
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse, ReadInputRegistersResponse
from pymodbus.bit_write_message import WriteMultipleCoilsResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse
from cpstwinning.hmimessages import CloseMessage, ReadMessage, WriteMessage, ReadMessageResult, SuccessHmiMessage, \
    FailedHmiMessage

import sys
import logging
import utils
import os

UNIT = 0x01
TIMEOUT = 100

# Logging
logging.basicConfig(filename=LOG_FILE_LOC, level=LOG_LEVEL)
logger = logging.getLogger('hmi_mb_client')


class HmiMbClient(object):

    def __init__(self, name):
        self.name = name
        mb_tbls = ModbusTables()
        self.actions = ('read', 'write')
        self.mb_tbls = {
            mb_tbls.CO: {self.actions[0]: self.read_coils, self.actions[1]: self.write_coils},
            mb_tbls.DI: {self.actions[0]: self.read_discrete_inputs},
            mb_tbls.HR: {self.actions[0]: self.read_holding_registers, self.actions[1]: self.write_registers},
            mb_tbls.IR: {self.actions[0]: self.read_input_registers}
        }
        self.__init_listener()

    def __init_listener(self):
        tmp_base = utils.get_tmp_base_path_from_mkfile()
        hmi_base_path = os.path.join(tmp_base, self.name)
        # Create HMI base path if it does not exist
        if not os.path.exists(hmi_base_path):
            os.makedirs(hmi_base_path)
        address = os.path.join(hmi_base_path, 'mb_socket')
        # Ensure that socket does not exist
        try:
            os.unlink(address)
        except OSError:
            if os.path.exists(address):
                logger.exception('Could not remove socket file.')
        # Create listener
        listener = Listener(address)
        while True:
            conn = listener.accept()
            msg = conn.recv()
            if isinstance(msg, ReadMessage):
                conn.send(self.mb_tbls[msg.mb_table][self.actions[0]](msg.ip, msg.starting_addr))
            elif isinstance(msg, WriteMessage):
                conn.send(self.mb_tbls[msg.mb_table][self.actions[1]](msg.ip, msg.starting_addr, msg.values))
            elif isinstance(msg, CloseMessage):
                conn.close()
                break
        listener.close()

    def read_coils(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_coils(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadCoilsResponse) and len(result.bits):
                return ReadMessageResult(result.bits[0])

    def read_holding_registers(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_holding_registers(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadHoldingRegistersResponse) and len(result.registers):
                return ReadMessageResult(result.registers[0])

    def read_input_registers(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_input_registers(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadInputRegistersResponse) and len(result.registers):
                return ReadMessageResult(result.registers[0])

    def read_discrete_inputs(self, ip, address):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.read_discrete_inputs(address - 1, 1, unit=UNIT)
            if isinstance(result, ReadDiscreteInputsResponse) and len(result.bits):
                return ReadMessageResult(result.bits[0])

    def write_coils(self, ip, address, values):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.write_coils(address - 1, values, unit=UNIT)
            if isinstance(result, WriteMultipleCoilsResponse):
                return SuccessHmiMessage()
        return FailedHmiMessage()

    def write_registers(self, ip, address, values):
        with ModbusTcpClient(ip, timeout=TIMEOUT) as client:
            result = client.write_registers(address - 1, values, unit=UNIT)
            if isinstance(result, WriteMultipleRegistersResponse):
                return SuccessHmiMessage()
        return FailedHmiMessage()


def main():
    if len(sys.argv) != 2:
        raise RuntimeError('Wrong number of arguments. Usage: python hmi_mb_client.py <name>')
    HmiMbClient(sys.argv[1])


if __name__ == '__main__':
    main()
