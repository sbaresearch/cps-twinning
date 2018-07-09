#!/usr/bin/env python

import re
from datetime import datetime

fmt = '%Y-%m-%d,%H:%M:%S.%f'

pattern = re.compile(
    '^(\d{4}[-]?\d{1,2}[-]?\d{1,2},\d{1,2}:\d{1,2}:\d{1,2}[\\.]?\d{1,3}) - .* - .* Issuing stimulus: \[.*,t=(\d+).*\].$')

timestamps = []

epoch = datetime.utcfromtimestamp(0)


# Cf. https://stackoverflow.com/a/11111177/5107545
def unix_time_millis(dt):
    return int((dt - epoch).total_seconds() * 1000.0)


with open(
        "cps-twinning.log",
        "r") as f:
    for line in f:
        match = pattern.match(line)
        if match:
            _t_virtual = match.group(1)
            t_physical = int(match.group(2))
            t_virtual = unix_time_millis(datetime.strptime(_t_virtual, fmt))
            timestamps.append((t_physical, t_virtual))

for t_p, t_v in timestamps:
    p = datetime.fromtimestamp(t_p / 1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    v = datetime.fromtimestamp(t_v / 1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print "{}, {}".format(t_p, t_v)


#delta_t = []
#
#i = 0
#for t_p, t_v in timestamps:
#    if i == 0:
#        delta_t.append((0, 0))
#    else:
#        delta_p = t_p - timestamps[i - 1][0]
#        delta_v = t_v - timestamps[i - 1][1]
#        delta_t.append((delta_p, delta_v))
#    i = i + 1

delta_t_sum = []
j = 0
for t_p, t_v in timestamps:
    if j == 0:
        delta_t_sum.append((0, 0))
    else:
        delta_p = t_p - timestamps[0][0]
        delta_v = t_v - timestamps[0][1]
        delta_t_sum.append((delta_p, delta_v))
    j = j + 1

header = [('physical', 'virtual')]
result = header + delta_t_sum
out = ""
for _, d in enumerate(result):
    out = out + ','.join(str(x) for x in d) + '\n'

print out
