#!/usr/bin/env python

from multiprocessing.connection import Client
from cpstwinning.plc_supervisor import UnknownPlcTagException

import argparse
import sys

class PlcSupervisorClient(object):
    
    def __init__(self):
        self.parse_args()
        
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--start", action='store_true', help="starts the PLC")
        parser.add_argument("--stop", action='store_true', help="stops the PLC")
        parser.add_argument("--tags", action='store_true', help="display a PLC's tags")
        parser.add_argument("--terminate", action='store_true', help="terminates the PLC supervisor")
        parser.add_argument("--get", help="display a tag's value")
        parser.add_argument("--monitor", nargs='+', help="monitors a PLC's tag")
        parser.add_argument("--set", action='append',
               type=lambda kv: kv.split("="), dest='set', help="set a tag's value")
        args = parser.parse_args()
        # TODO: Implement proper validation
        if args.start:
            self.start()
        elif args.stop:
            self.stop()
        elif args.tags:
            self.show_tags()
        elif args.get:
            self.get_var_value(args.get)
        elif args.set:
            for k, v in dict(args.set).iteritems():
                self.set_var_value(k, v)
            self.__close()
        elif args.monitor:
            self.monitor(args.monitor)
        elif args.terminate:
            self.terminate()
        else:
            self.error('Invalid args.')

    def start(self):
        self.__send('start')
        result = self.conn.recv()
        self.output(result)
        self.__close()
        
    def stop(self):
        self.__send('stop')
        result = self.conn.recv()
        self.output(result)
        self.__close()

    def get_var_value(self, name):
        self.__send('get {}'.format(name))
        try:
            result = self.conn.recv()
            if isinstance(result, UnknownPlcTagException):
                raise UnknownPlcTagException(result)
            else:
                self.output(str(result) + '\n')
        except UnknownPlcTagException as e:
            self.error(e.message)
        self.__close()

    def set_var_value(self, name, value):
        self.__send('set {}={}'.format(name, value))
        try:
            result = self.conn.recv()
            if isinstance(result, UnknownPlcTagException):
                raise UnknownPlcTagException(result)
            else:
                self.output(result)
        except UnknownPlcTagException as e:
            self.error(e.message)

    def terminate(self):
        self.__send('terminate')
        self.__close()

    def show_tags(self):
        self.__send('show_tags')
        vars = self.conn.recv()
        titles = ["Name", "Class", "Type"]
        # Will contain: { 'name': [...], 'class': [...], 'type': [...] }
        transposed_vars = {}
        for d in vars:
            for k, v in d.items():
                transposed_vars.setdefault(k, []).append(v)
        data = [titles] + list(zip(transposed_vars['name'], transposed_vars['class'], transposed_vars['type']))
        out = ""
        for i, d in enumerate(data):
            out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        self.output(out)
        self.__close()
        
    def monitor(self, vars):
        self.__send('monitor {}'.format(' '.join(vars)))
        try:
            while True:
                result = self.conn.recv()
                name = result['name']
                val = result['value']
                self.output('{},{}'.format(name, val))
        except KeyboardInterrupt:
            self.__close()

    def __create_connection(self):
        address = ('localhost', 6000)
        self.conn = Client(address)
    
    def __send(self, msg):
        self.__create_connection()
        self.conn.send(msg)
        
    def __close(self):
        self.conn.close()
    
    def output(self, out, flush=True):
        print out
        # Flushing stdout immediately after print is necessary,
        # when monitoring a PLC's variable.
        if flush:
            sys.stdout.flush()
            
    def error(self, errmsg):
        print 'ERROR: {}'.format(errmsg)


def main():
    PlcSupervisorClient()


if __name__ == '__main__':
    main()
