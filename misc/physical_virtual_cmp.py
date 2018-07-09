#!/usr/bin/env python

import argparse
import re
import csv
from itertools import izip, islice
from datetime import datetime


class PhysicalVirtualCmp(object):

    def __init__(self, virtual, physical, plc_name, steps):
        self.f_virtual = virtual
        self.f_phyiscal = physical
        self.plc_name = plc_name
        self.steps = steps
        self.physical_logs = self.__get_physical_logs()
        self.virtual_logs = self.__get_virtual_logs()
        self.physical_logs_diff = ['-'] + self.__get_logs_diff(self.physical_logs, '%Y-%m-%d %H:%M:%S.%f')
        self.virtual_logs_diff = ['-'] + self.__get_logs_diff(self.virtual_logs, '%Y-%m-%d %H:%M:%S.%f')

    def __get_virtual_logs(self):
        # Should match  the following log format:
        # 2018-06-12,06:55:29.771 - p13819 {/home/wifi/cps-twinning/cpstwinning/statelogging.py:98} - twin_state - INFO - [2018-06-12 06:55:29.771] 'PLC1' variable changed [CONVEYORRUN=True].
        pattern = re.compile(
            '^.* - \[(\d{4}[-]?\d{1,2}[-]?\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}[\\.]?\d{1,3})\] \'(\S+)\'.* \[(\S+)\=(\S+)\]\.$'
        )
        virtual_logs = []
        step_count = 0
        for line in self.f_virtual:
            match = pattern.match(line)
            if match:
                timestamp = match.group(1)
                twin_name = match.group(2)
                var_name = match.group(3)
                var_val = match.group(4)
                if twin_name == self.plc_name:
                    curstep_k, curstep_v = self.steps[step_count]
                    if var_name == curstep_k and var_val == curstep_v:
                        virtual_logs.append(timestamp)
                        step_count = step_count + 1
            if step_count >= len(steps):
                break
        return virtual_logs

    def __get_physical_logs(self):
        physical_logs = []
        field_names = []
        step_count = 0
        f_physical_reader = csv.reader(self.f_phyiscal, skipinitialspace=True, delimiter=',', quotechar='|')
        for row in f_physical_reader:
            if not len(field_names):
                field_names = row
                continue

            # This flag will be true if field value in row does not equal corresponding step value.
            # We use this flag to process more than one row field in one iteration.
            row_checked = False
            while not row_checked:
                curstep_k, curstep_v = self.steps[step_count]
                log_value = row[field_names.index(curstep_k)]
                # print 'k={}, v={}, value={}, step={}'.format(curstep_k, curstep_v, log_value, step_count)
                if curstep_v == 'True' or curstep_v == 'False':
                    curstep_v = int(curstep_v == 'True')
                else:
                    curstep_v = int(curstep_v)
                if int(log_value) == curstep_v:
                    # Log entry matches current step
                    physical_logs.append(row[1])
                    step_count = step_count + 1
                else:
                    row_checked = True

                # If we have processed all steps, return
                if step_count >= len(steps):
                    return physical_logs

    def __get_logs_diff(self, logs, fmt):
        diff = []
        # Cf. https://stackoverflow.com/a/5434929/5107545
        for current_item, next_item in izip(logs, islice(logs, 1, None)):
            diff.append(self.__get_diff_ms(current_item, next_item, fmt))
        return diff

    def __get_diff_ms(self, x, y, fmt):
        a = datetime.strptime(x, fmt)
        b = datetime.strptime(y, fmt)
        delta = b - a
        ms = (delta.seconds * 1000) + (delta.microseconds / 1000)
        return ms

    def show(self):
        def get_diff_physical_virtual(a, b):
            data = zip(a, b)
            diff = []
            for p, v in data:
                if p == '-' or v == '-':
                    diff.append('-')
                else:
                    diff.append(v - p)
            return diff

        header = [('Change', 'Physical', 'Physical Diff (ms)', 'Virtual', 'Virtual Diff (ms)', 'Diff (ms)')]
        steps_joined = ('='.join(w) for w in self.steps)
        result = header + \
                 zip(
                     steps_joined,
                     self.physical_logs,
                     self.physical_logs_diff,
                     self.virtual_logs,
                     self.virtual_logs_diff,
                     get_diff_physical_virtual(self.physical_logs_diff, self.virtual_logs_diff)
                 )
        out = ""
        for i, d in enumerate(result):
            out = out + '|'.join(str(x).ljust(30) for x in d) + '\n'
            if i == 0:
                out = out + '-' * len(out) + '\n'
        print out

    def csv(self):
        header = [('step', 'physical', 'virtual')]
        steps_joined = ('='.join(w) for w in self.steps)
        physical = self.physical_logs_diff
        physical[0] = 0
        virtual = self.virtual_logs_diff
        virtual[0] = 0
        result = header + \
                 zip(
                     steps_joined,
                     physical,
                     virtual
                 )
        out = ""
        for i, d in enumerate(result):
            out = out + ','.join(str(x) for x in d) + '\n'
        print out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compare temporal differences between the physical and virtual environment.')
    parser.add_argument('--virtual', type=argparse.FileType('r'), help='path to cps-twinning-states.log')
    parser.add_argument('--physical', type=argparse.FileType('r'), required=True,
                        help='path to PLC log')
    parser.add_argument('--plc', required=True, help='name of the PLC')
    parser.add_argument('--steps', nargs='+', required=True, help='steps to compare')
    parser.add_argument('--csv', help='true, if csv should be printed', action='store_true')
    args = parser.parse_args()
    plc_name = args.plc
    # Split list: ['STARTCONVEYORBELT'='True', ...] into [('STARTCONVEYORBELT', 'True'), ...] list of tuples
    steps = list(map(lambda x: tuple(x.split('=')), args.steps))
    physical_virtual_cmp = PhysicalVirtualCmp(args.virtual, args.physical, plc_name, steps)
    if args.csv:
        physical_virtual_cmp.csv()
    else:
        physical_virtual_cmp.show()
    # Close files
    args.physical.close()
    args.virtual.close()
