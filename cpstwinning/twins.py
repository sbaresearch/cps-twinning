#!/usr/bin/env python

from mininet.util import pmonitor
from mininet.node import Host
from threading import Event, Thread

import sys
import os
import utils
import pickle
import logging

# Logging
logging.basicConfig(filename='/tmp/cps-twinning.log', level=logging.DEBUG)


class Plc(Host):
    "A PLC host."
    
    def config(self, **params):
        super(Plc, self).config(**params)
        # TODO: Error handling
        st_path = params.pop('st_path', None)
        mb_map = params.pop('mb_map', None)
        mb_map_path = self.__persist_mb_map(mb_map) if mb_map is not None else ''
        self._plc_supervisor_client_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor_client.py')
        plc_supervisor_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor.py')
        cmd = '{} {} {} {} {} &'.format(sys.executable, plc_supervisor_path, self.name, st_path, mb_map_path)
        self.cmd(cmd)
        
    def __persist_mb_map(self, mb_map):
        dir_path = utils.get_dstdir_path_from_mkfile(self.name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        path = os.path.join(dir_path, 'mb_map.txt')
        with open(path, 'wb') as handle:
            pickle.dump(mb_map, handle)
        return path
    
    def terminate(self):
        self.cmd('{} --terminate'.format(self.__get_base_supervisor_client_cmd()))
        super(Plc, self).terminate()

    def start(self):
        return self.__printCmd('--start')
        
    def stop(self):
        return self.__printCmd('--stop')
        
    def get_var_value(self, name):
        return self.__printCmd('--get {}'.format(name))

    def set_var_value(self, name, value):
        self.cmd('{} --set {}={}'.format(self.__get_base_supervisor_client_cmd(), name, value))
    
    def show_tags(self):
        return self.__printCmd('--tags')
    
    def __get_base_supervisor_client_cmd(self):
        return '{} {}'.format(sys.executable, self._plc_supervisor_client_path)
    
    def __printCmd(self, flag):
        popens = {}
        popens[ "plc" ] = self.popen('{} {}'.format(self.__get_base_supervisor_client_cmd(), flag))
        out = ""
        for host, line in pmonitor(popens):
            if host:
                out = out + line
        return out


class Hmi(Host):
    "An HMI host."
    
    def config(self, **params):
        super(Hmi, self).config(**params)
        self._hmi_mb_client_path = os.path.join(utils.get_pkg_path(), 'hmi_mb_client.py')
        # TODO: Replace with parser vars
        self.vars = [{'name': 'Start', 'mb_table': 'hr', 'mb_addr': 1, 'value': False}, {'name': 'Stop', 'mb_table': 'hr', 'mb_addr': 2, 'value': False}, {'name': 'Velocity', 'mb_table': 'hr', 'mb_addr': 3, 'value': 0}]
        self.var_link_clbk = None
        
    def set_var_link_clbk(self, clbk):
        self.var_link_clbk = clbk
        
    def get_var_value(self, name):
        for var in self.vars:
            if var['name'] == name:
                popens = {}
                args = '192.168.0.1 --read {} {}'.format(var['mb_table'], var['mb_addr'])
                popens[ "hmi" ] = self.popen('{} {}'.format(self.__get_base_hmi_mb_client_cmd(), args))
                val_set = False
                for host, line in pmonitor(popens):
                    if host:
                        val = line.strip()
                        if type(var['value']) is int:
                            var['value'] = int(val)
                        elif type(var['value']) is bool:
                            # Value received via Modbus may be 0/1 
                            var['value'] = val == 'True' or val == '1'
                        else:
                            raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                        val_set = True
                if not val_set:
                    logging.error('Modbus request timed out.')
                else:
                    if self.var_link_clbk is not None:
                        self.var_link_clbk(var)
                return str(var['value']) + '\n'
        return "ERROR: Variable name '{}' does not exist in HMI.\n".format(name)
    
    def set_var_value(self, name, value):
        for var in self.vars:
            if var['name'] == name:
                old_value = var['value']
                # Optimistically set new value in HMI vars
                if type(var['value']) is int:
                    var['value'] = int(value)
                elif type(var['value']) is bool:
                    var['value'] = value == 'True'
                    # Convert boolean
                    value = 1 if var['value'] else 0
                else:
                    raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                popens = {}
                args = '192.168.0.1 --write {} {}={}'.format(var['mb_table'], var['mb_addr'], value)
                popens[ "hmi" ] = self.popen('{} {}'.format(self.__get_base_hmi_mb_client_cmd(), args))
                for host, line in pmonitor(popens):
                    if host and line:
                        # Error - rollback
                        var['value'] = old_value
                        return 'ERROR: ' + line
                    
                if self.var_link_clbk is not None:
                    self.var_link_clbk(var)
                        
        return "ERROR: Variable name '{}' does not exist in HMI.\n".format(name)
    
    def show_tags(self):
        titles = ["Name"]
        transposed_vars = {}
        for d in self.vars:
            for k, v in d.items():
                transposed_vars.setdefault(k, []).append(v)
        data = [titles] + list(zip(transposed_vars['name']))
        out = ""
        for i, d in enumerate(data):
            out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        return out
            
    def __get_base_hmi_mb_client_cmd(self):
        return '{} {}'.format(sys.executable, self._hmi_mb_client_path)
    

class Motor(object):
    "A motor."
   
    def __init__(self, name, vars, plc, plc_vars_map):
        self.name = name
        self.plc = plc
        self.vars = vars
        self.plc_vars_map = plc_vars_map  # Name of PLC var to map : Internal motor var
        self.motor_thread = MotorMonitorThread(self, plc)
        self.motor_thread.start()

    def get_status(self):
        titles = ["Name", "Value"]
        # Will contain: { 'name': [...], 'value': [...] }
        transposed_vars = {}
        for d in self.vars:
            for k, v in d.items():
                transposed_vars.setdefault(k, []).append(v)
        data = [titles] + list(zip(transposed_vars['name'], transposed_vars['value']))
        out = ""
        for i, d in enumerate(data):
            out = out + '|'.join(str(x).ljust(12) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        return out
    
    def __str__(self):
        return self.name

    
class MotorMonitorThread(Thread):
    
    def __init__(self, motor, plc):
        Thread.__init__(self)
        self.motor = motor
        self._plc_supervisor_client_path = os.path.join(utils.get_pkg_path(), 'plc_supervisor_client.py')
        self.plc = plc
    
    def __get_base_supervisor_client_cmd(self):
        return '{} {}'.format(sys.executable, self._plc_supervisor_client_path)
    
    def run(self):
        popens = {}
        str_of_vars = ' '.join(map(lambda x: str(x), self.motor.plc_vars_map.keys()))
        popens[ "plc" ] = self.plc.popen('{} --monitor {}'.format(self.__get_base_supervisor_client_cmd(), str_of_vars))
        for host, line in pmonitor(popens):
            if host:
                l = line.strip()
                spl_l = l.split(',')
                if len(spl_l) != 2:
                    print "ERROR. Received unknown line {}.\n".format(l)
                else:
                    name, val = spl_l
                    motor_var_idx = self.motor.plc_vars_map[name]
                    var = self.motor.vars[motor_var_idx]['value']
                    if type(var) is int:
                        self.motor.vars[motor_var_idx]['value'] = int(val)
                    elif type(var) is bool:
                        self.motor.vars[motor_var_idx]['value'] = val == 'True'
                    else:
                        raise RuntimeError('Unsupported type \'{}\'.'.format(type(var)))
                    
