#!/usr/bin/env python


class HmiMessage(object):

    def __init__(self):
        pass


class CloseMessage(HmiMessage):

    def __init__(self):
        super(CloseMessage, self).__init__()


class HmiModbusMessage(HmiMessage):

    def __init__(self, ip, mb_table):
        super(HmiModbusMessage, self).__init__()
        self.ip = ip
        self.mb_table = mb_table


class ReadMessage(HmiModbusMessage):

    def __init__(self, ip, mb_table, starting_addr, quantity=1):
        super(ReadMessage, self).__init__(ip, mb_table)
        self.starting_addr = starting_addr
        self.quantity = quantity


class ReadMessageResult(object):

    def __init__(self, value):
        self.value = value


class WriteMessage(HmiModbusMessage):

    def __init__(self, ip, mb_table, starting_addr, quantity, values):
        super(WriteMessage, self).__init__(ip, mb_table)
        self.starting_addr = starting_addr
        self.quantity = quantity
        self.values = values


class SuccessHmiMessage(HmiMessage):

    def __init__(self):
        super(SuccessHmiMessage, self).__init__()


class FailedHmiMessage(HmiMessage):

    def __init__(self):
        super(FailedHmiMessage, self).__init__()
