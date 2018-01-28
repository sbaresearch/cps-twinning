#!/usr/bin/env python

from cpstwinning.cpstw import CpsTwinning
from cpstwinning.cpstwrt import CpsTwinningRuntime
from cpstwinning.cli import CpsTwinningCli as CLI

import sys


class CpsTwinningMain(CpsTwinningRuntime):

    def __init__(self, name, net):

        self.name = name
        self.net = net

        CLI(self.net)

        net.stop()


if __name__ == "__main__":

    net = CpsTwinning()

    demo = CpsTwinningMain(
        name='cps_twinning',
        net=net)
