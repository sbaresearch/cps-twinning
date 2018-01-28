#!/usr/bin/env python

from mininet.net import Mininet
from cpstwinning.cli import CpsTwinningCli as CLI


class CpsTwinningRuntime(object):

    def __init__(self, name, net):
        self.name = name
        self.net = net

        self.net.start()
        CLI(self.net)
        self.net.stop()
