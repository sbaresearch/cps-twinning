#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from utils import get_pkg_path
from os import path, sep
from cpstwinning.twins import Plc, Hmi, Motor
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from multiprocessing.connection import Client
from cpstwinning.plcmessages import TerminateMessage, MonitorMessage, MonitorResponseMessage, GetTagMessage, \
    GetTagResponseMessage, GetAllTagNamesMessage, GetAllTagNamesResponseMessage
from cpstwinning.utils import UnknownPlcTagException
from time import sleep
from errno import ENOENT

import json
import logging
import re
import os
import utils
import socket
import threading

logger = logging.getLogger(__name__)
WEB_BASE = 'viz'
VIZ_DATA_FILENAME = 'data.json'

rest_twin_pattern_obj = re.compile(r'/api/v1/([_a-zA-Z0-9]+)/?')


def get_viz_http_handler(cpstw):
    class VizHttpHandler(BaseHTTPRequestHandler):

        def __init__(self, request, client_address, server):
            self.cpstw = cpstw
            BaseHTTPRequestHandler.__init__(self, request, client_address, server)

        def _set_headers(self, code, content_type):
            self.send_response(code)
            self.send_header('Content-type', content_type)
            self.end_headers()

        def do_GET(self):

            def send_404():
                self.send_error(404, 'File Not Found: %s' % self.path)

            def get_resource_path(name):
                return path.join(get_pkg_path(), WEB_BASE + sep + name)

            try:
                if self.path == "/":
                    with open(get_resource_path('index.html')) as f:
                        self._set_headers(200, 'text/html')
                        self.wfile.write(f.read())
                elif self.path.endswith(".js") or self.path.endswith(".min.js") or self.path.endswith(".js.map"):
                    with open(get_resource_path(self.path)) as f:
                        self._set_headers(200, 'application/javascript')
                        self.wfile.write(f.read())
                elif self.path.endswith(".css") or self.path.endswith(".min.css") or self.path.endswith(".min.css.map"):
                    with open(get_resource_path(self.path)) as f:
                        self._set_headers(200, 'text/css')
                        self.wfile.write(f.read())
                elif self.path.endswith(".json"):
                    with open(get_resource_path(self.path)) as f:
                        self._set_headers(200, 'application/json')
                        self.wfile.write(f.read())
                elif rest_twin_pattern_obj.match(self.path):
                    twin_name = rest_twin_pattern_obj.match(self.path).group(1)
                    if twin_name in self.cpstw:
                        twin = self.cpstw[twin_name]
                    # Check if twin is physical device (e.g., motor)
                    elif any(d.name == twin_name for d in self.cpstw.physical_devices):
                        twin = [d for d in self.cpstw.physical_devices if d.name == twin_name][0]
                    else:
                        logger.info("Requested twin '%s' does not exist.", twin_name)
                        send_404()
                        return
                    if isinstance(twin, Plc) or isinstance(twin, Hmi) or isinstance(twin, Motor):
                        self._set_headers(200, 'application/json')
                        self.wfile.write(json.dumps(twin.get_vars()))
                    else:
                        logger.info("Requested twin '%s' is not PLC, HMI or Motor, but '%s'.", twin_name, type(twin))
                        send_404()
                else:
                    logger.info("Nothing matches the given URI [path={}].".format(self.path))
                    send_404()
            except IOError:
                logger.info("Nothing matches the given URI [path={}].".format(self.path))
                send_404()

        def log_message(self, msg_format, *args):
            logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), msg_format % args))

    return VizHttpHandler


class VizHttpServer(Thread):

    def __init__(self, cpstw, port=80):
        Thread.__init__(self)
        self.cpstw = cpstw
        self._httpd = None
        self._port = port

    def run(self):
        self._httpd = HTTPServer(('', self._port), get_viz_http_handler(self.cpstw))
        self._httpd.serve_forever()

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()


def get_viz_websocket_handler(cpstw):
    device_to_client_map = {}

    class VariableMonitoringThread(Thread):

        def __init__(self, **kwargs):
            Thread.__init__(self)
            # If PLC name is set, we monitor all PLC tags
            self.plc_name = kwargs.get('plc_name', None)
            self.motor = None
            # If no PLC name is set, we check if motor tags should be monitored
            if self.plc_name is None:
                self.motor = kwargs.get('motor', None)
                # No motor supplied, building thread failed. Either PLC name (for monitoring all PLC tags) or motor
                # (for monitoring motor/PLC tags) must be supplied
                if self.motor is None:
                    raise ValueError("No PLC name or motor supplied.")
                else:
                    self.plc_name = self.motor.plc.name
            self.listener_ready = False

        def __create_connection(self):
            tmp_base = utils.get_tmp_base_path_from_mkfile()
            plc_base_path = os.path.join(tmp_base, self.plc_name)
            address = os.path.join(plc_base_path, 'plc_socket')
            # Wait until listener is ready
            # TODO: Refactoring needed (anti-pattern)
            while not self.listener_ready:
                try:
                    self.conn = Client(address)
                    self.listener_ready = True
                except socket.error as e:
                    # Check if listener is not yet ready
                    if e.errno == ENOENT:  # socket.error: [Errno 2] No such file or directory
                        sleep(1)
                    else:
                        logger.exception("Unknown socket error occurred.")

        def run(self):
            self.__create_connection()
            tag_names = []
            # If motor is none, all PLC tags should be monitored
            if self.motor is None:
                self.conn.send(GetAllTagNamesMessage())
            else:
                tag_names = self.motor.plc_vars_map.keys()
                self.conn.send(MonitorMessage(tag_names))
            while True:
                try:
                    result = self.conn.recv()
                    if isinstance(result, UnknownPlcTagException):
                        raise UnknownPlcTagException(result)
                    elif isinstance(result, TerminateMessage):
                        logger.info("Terminating monitoring of '{}'.".format(', '.join(tag_names)))
                        break
                    elif isinstance(result, GetAllTagNamesResponseMessage):
                        tag_names = result.tag_names
                        # Recreate connection before sending new message
                        self.listener_ready = False
                        self.__create_connection()
                        self.conn.send(MonitorMessage(tag_names))
                    elif isinstance(result, MonitorResponseMessage):
                        dev_name = None
                        # First check if we are currently monitoring a PLC or motor
                        if self.motor is None:
                            # We are monitoring a PLC
                            if self.plc_name in device_to_client_map:
                                dev_name = self.plc_name
                        else:
                            if self.motor.name in device_to_client_map:
                                dev_name = self.motor.name
                                # We have to alter the name of the result set, as we are receiving PLC tag
                                # changes, yet we have to transmit the motor tag
                                # The 'plc_vars_map' will contain the mapping: {PLC_TAG_NAME: IDX_MOTOR_VARS}
                                idx_motor_var = self.motor.plc_vars_map.get(result.name)
                                if idx_motor_var is not None:
                                    # Set the correct motor tag name
                                    result.name = self.motor.vars[idx_motor_var]['name']
                                else:
                                    logger.error("Received unknown PLC tag (motor tag map).")

                        if dev_name is not None:
                            # logger.info("'%s' variable changed [%s=%s].", dev_name, result.name, result.value)
                            for client in device_to_client_map[dev_name]:
                                client.sendMessage(
                                    u"" + json.dumps({'tag_change': {'name': result.name, 'value': result.value}}))
                    else:
                        logger.error("Received unexpected message type '%s'.", type(result))
                except EOFError:
                    logger.exception("Received EOF.")
                    break
                except UnknownPlcTagException:
                    logger.exception("Unknown PLC Tag.")

            self.conn.close()

    def hmi_tag_callback(hmi, name, value):
        logger.debug("HMI '%s' variable changed [%s=%s].", hmi.name, name, value)
        if hmi.name in device_to_client_map:
            for client in device_to_client_map[hmi.name]:
                client.sendMessage(
                    u"" + json.dumps({'tag_change': {'name': name, 'value': value}}))

    for node in cpstw.values():
        if isinstance(node, Plc):
            plc_mon_thread = VariableMonitoringThread(plc_name=node.name)
            plc_mon_thread.start()
        elif isinstance(node, Hmi):
            node.add_var_monitor_clbk(hmi_tag_callback)

    for device in cpstw.physical_devices:
        if isinstance(device, Motor):
            motor_mon_thread = VariableMonitoringThread(motor=device)
            motor_mon_thread.start()

    class VizWebsocketHandler(WebSocket):

        def handleMessage(self):
            result = json.loads(self.data)
            if 'subscribe' in result:
                dev_name = result['subscribe']
                nodes_list = cpstw.values() + cpstw.physical_devices
                for twin in nodes_list:
                    if twin.name == dev_name:
                        if dev_name not in device_to_client_map:
                            device_to_client_map[dev_name] = [self]
                        else:
                            # Check if client already subscribed to device
                            if self in device_to_client_map[dev_name]:
                                return
                            # Client has not yet subscribed to device, so create subscription
                            device_to_client_map[dev_name].append(self)
                        logger.debug("Client %s:%s subscribed to '%s'.", self.address[0], self.address[1], dev_name)
                        return
                logger.error("Client %s:%s attempted to subscribe to unknown device '%s'.", self.address[0],
                             self.address[1], dev_name)

            elif 'unsubscribe' in result:
                for sub_dev in result['unsubscribe']:
                    if sub_dev in device_to_client_map:
                        device_to_client_map[sub_dev].remove(self)
                        logger.debug("Client %s:%s unsubscribed from device '%s'.", self.address[0],
                                     self.address[1], sub_dev)
                    else:
                        logger.error("Client %s:%s attempted to unsubscribe from device '%s'.", self.address[0],
                                     self.address[1], sub_dev)

            else:
                logger.debug("Received unknown action '%s' from client %s:%s.", result['subscribe'], self.address[0],
                             self.address[1])

        def handleConnected(self):
            logger.debug("Client %s:%s connected.", self.address[0], self.address[1])

        def handleClose(self):
            logger.debug("Client %s:%s closed connection.", self.address[0], self.address[1])

    return VizWebsocketHandler


class VizWebsocketServer(Thread):

    def __init__(self, cpstw, port=8000):
        Thread.__init__(self)
        self.cpstw = cpstw
        self._websocketd = None
        self._port = port
        self.stop_event = threading.Event()

    def run(self):
        self._websocketd = SimpleWebSocketServer('', self._port, get_viz_websocket_handler(self.cpstw))
        while not self.stop_event.is_set():
            self._websocketd.serveonce()
        self._websocketd.close()

    def stop(self):
        logger.info("Stopping VizWebsocketServer now!")
        self.stop_event.set()


class Viz(object):

    def __init__(self, cpstw, parser):
        self.cpstw = cpstw
        self.parser = parser
        self.running = False
        self._httpd = None
        self._websocketd = None

    def __start_httpd(self):
        self._httpd = VizHttpServer(self.cpstw)
        self._httpd.start()

    def __stop_httpd(self):
        if self._httpd is not None:
            self._httpd.stop()
        else:
            logger.error("httpd has not yet been started. Nothing to stop!")

    def __start_websocketd(self):
        self._websocketd = VizWebsocketServer(self.cpstw)
        self._websocketd.start()

    def __stop_websocketd(self):
        if self._websocketd is not None:
            self._websocketd.stop()
        else:
            logger.error("websocketd has not yet been started. Nothing to stop!")

    def __init_viz_data(self):

        def get_links(nodes):
            def get_idx_in_nodes(name):
                for i, dic in enumerate(nodes):
                    logger.debug(dic)
                    if dic['name'] == name:
                        return i
                return -1

            def get_motor_links():
                """Returns links between PLCs and Motors (physical devices)."""
                lks = []
                # I/O links are currently limited to PLC only
                for motor in self.parser.motors:
                    idx_motor = get_idx_in_nodes(motor['name'])
                    if idx_motor == -1:
                        logger.error("Could not find motor in nodes array.")
                        continue
                    if motor['plc_name']:
                        idx_plc = get_idx_in_nodes(motor['plc_name'])
                        if idx_plc == -1:
                            logger.error("Could not find PLC in nodes array.")
                            continue
                        lks.append({"source": idx_motor, "target": idx_plc, "type": "io"})
                return lks

            def get_switch_ap_links(node_arr, link_type):
                """Returns links from Switches or Access Points based on AML parsing results."""
                # cola-format: { "source": 1, "target": 2 }
                # aml-data-struct: {'name': 'Switch1', 'links': ['HMI1', 'PLC1']}
                lks = []
                for node in node_arr:
                    idx_node = get_idx_in_nodes(node['name'])
                    if idx_node == -1:
                        logger.error("Could not find node [name={}] in nodes array.".format(node['name']))
                        continue
                    for lk in node['links']:
                        idx_link = get_idx_in_nodes(lk)
                        if idx_link == -1:
                            logger.error("Could not find link in nodes array.")
                            continue
                        lks.append({"source": idx_node, "target": idx_link, "type": link_type})
                return lks

            return get_switch_ap_links(self.parser.switches, 'wired-network') + \
                   get_switch_ap_links(self.parser.aps, 'wireless-network') + \
                   get_motor_links()

        def get_nodes():

            def get_node(val, node_type=None):
                name = val['name']
                node = {
                    "id": name.lower(),
                    "name": name,
                }
                if 'network' in val:
                    node['network'] = val['network']
                if node_type is not None:
                    node['type'] = node_type
                return node

            nds = []

            type_mapping = [
                (self.parser.plcs, 'plc'),
                (self.parser.hmis, 'hmi'),
                (self.parser.switches, 'switch'),
                (self.parser.motors, 'motor'),
                (self.parser.aps, 'ap'),
                (self.parser.mqttbrkrs, 'mqttbrkr'),
                (self.parser.rfidrs, 'rfidr'),
                (self.parser.iiotgws, 'iiotgw')
            ]

            for (arr, n_type) in type_mapping:
                for node in arr:
                    nds.append(get_node(node, n_type))

            return nds

        def get_data():
            nodes = get_nodes()
            links = get_links(nodes)
            return {"nodes": nodes, "groups": [], "links": links}

        data_file_path = path.join(get_pkg_path(), WEB_BASE + sep + VIZ_DATA_FILENAME)
        # data = json.load(open(path.join(get_pkg_path(), WEB_BASE + sep + VIZ_DATA_FILENAME)))
        data = get_data()
        with open(data_file_path, 'w') as outfile:
            json.dump(data, outfile)
        logger.debug(data)

    def start(self):
        if not self.running:
            logger.debug("Starting viz...")
            self.__init_viz_data()
            self.__start_httpd()
            self.__start_websocketd()
            self.running = True
        else:
            logger.info("Viz module already started. Nothing to do...")

    def stop(self):
        if self.running:
            logger.debug("Stopping viz...")
            self.__stop_httpd()
            self.__stop_websocketd()
            self.running = False
        else:
            logger.info("Viz module already stopped. Nothing to do...")
