#!/usr/bin/env python

from mininet.wifi.cli import CLI_wifi
from mininet.log import output, error
from cpstwinning.twins import Plc, Motor, Hmi, RfidReaderMqttWiFi


class CpsTwinningCli(CLI_wifi):
    # Override 'mininet' prompt text
    prompt = 'cpstwinning> '

    def do_twinning(self, line):
        """Starts the twinning process.
           Usage: twinning <path_to_aml>
        """
        args = line.split()
        if len(args) != 1:
            error('Invalid number of args: twinning <path to aml>\n')
            return
        else:
            self.mn.twinning(args[0])

    def do_get_tag(self, line):
        """Retrieves a tag from a PLC.
           Usage: get_tag <plc_name> <tag_name>
        """
        args = line.split()
        if len(args) != 2:
            error('Invalid number of args: get_tag <plc_name> <tag_name>\n')
            return
        for node in self.mn.values():
            if node.name == args[0]:
                if isinstance(node, Plc) or isinstance(node, Hmi):
                    output(node.get_var_value(args[1]))
                    return
        error("No PLC or HMI found with name '{}'.\n".format(args[0]))

    def do_set_tag(self, line):
        """Sets a tag in a PLC.
           Usage: set_tag <plc_name> <tag_name> <value>
        """
        args = line.split()
        if len(args) != 3:
            error('Invalid number of args: set_tag <plc_name> <tag_name> <value>\n')
            return
        for node in self.mn.values():
            if node.name == args[0]:
                if isinstance(node, Plc) or isinstance(node, Hmi):
                    output(node.set_var_value(args[1], args[2]))
                    return
        error("No PLC or HMI found with name '{}'.\n".format(args[0]))

    def do_show_tags(self, line):
        """Shows all available tags of a PLC.
           Usage: show_tags <plc_name>
        """
        args = line.split()
        if len(args) != 1:
            error('Invalid number of args: show_tags <plc_name>\n')
            return
        for node in self.mn.values():
            if node.name == args[0]:
                if isinstance(node, Plc) or isinstance(node, Hmi):
                    output(node.show_tags())
                return
        error("No PLC or HMI found with name '{}'.\n".format(args[0]))

    def do_stop_plc(self, line):
        """Stops a PLC.
           Usage: stop_plc <plc_name>
        """
        args = line.split()
        if len(args) != 1:
            error('Invalid number of args: stop_plc <plc_name>\n')
            return

        for node in self.mn.values():
            if node.name == args[0] and isinstance(node, Plc):
                output(node.stop())
                return
        error("No PLC found with name '{}'.\n".format(args[0]))

    def do_start_plc(self, line):
        """Starts a PLC.
           Usage: start_plc <plc_name>
        """
        args = line.split()
        if len(args) != 1:
            error('Invalid number of args: start_plc <plc_name>\n')
            return

        for node in self.mn.values():
            if node.name == args[0] and isinstance(node, Plc):
                output(node.start())
                return
        error("No PLC found with name '{}'.\n".format(args[0]))

    def do_show_motor_status(self, line):
        """Shows a motor's status.
           Usage: show_motor_status <motor_name>
        """
        args = line.split()
        if len(args) != 1:
            error('Invalid number of args: show_motor_status <motor_name>\n')
            return
        devices = getattr(self.mn, 'physical_devices', [])
        for dev in devices:
            if dev.name == args[0] and isinstance(dev, Motor):
                output(dev.get_status())
                return
        error("No motor found with name '{}'.\n".format(args[0]))

    def do_devices(self, _line):
        """Lists all devices (motors, pumps etc.).
           Usage: devices
        """
        devices = getattr(self.mn, 'physical_devices', [])
        out = ' '.join(str(x) for x in devices) if devices else ''
        output('available devices are: \n{}\n'.format(out))

    def do_start_replication(self, _line):
        """Starts the replication module.
           Usage: start_replication
        """
        self.mn.start_replication()

    def do_stop_replication(self, _line):
        """Stops the replication module.
           Usage: stop_replication
        """
        self.mn.stop_replication()

      def do_rfid_read(self, line):
        """Reads a value by a RFID reader.
           Usage: rfid_read <rfid_reader_name> <value>
        """
        args = line.split()
        if len(args) != 2:
            error('Invalid number of args: nfc_read <nfc_reader_name> <value>\n')
            return
        for node in self.mn.values():
            if node.name == args[0]:
                if isinstance(node, RfidReaderMqttWiFi):
                    output(node.read_value(args[1]))
                    return
        error("No NFC reader found with name '{}'.\n".format(args[0]))

    def do_start_state_logging(self, _line):
        """Starts the visualization module.
           Usage: start_state_logging
        """
        self.mn.start_state_logging()

    def do_stop_state_logging(self, _line):
        """Stops the state logging module.
           Usage: stop_state_logging
        """
        self.mn.stop_state_logging()
