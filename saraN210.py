#!/usr/bin/python3
import saraN210Mem as Mem
from saraN210Mem import Types
import serial
import time
from _thread import *
from functools import partial
import random
import re
from ping3 import ping
import udpClient


def gen_response(command, cmd_type, value, cmd_len):
    if len(command) != cmd_len:
        return Mem.ERROR_RESPONSE
    if cmd_type == Types.Action or cmd_type == Types.Read:
        return '{}\r\n\r\n{}'.format(value, Mem.OK_RESPONSE)
    if cmd_type == Types.Test:
        return Mem.OK_RESPONSE
    else:
        return Mem.ERROR_RESPONSE


def gen_response_test(command, cmd_type, value, test, cmd_len):
    if len(command) != cmd_len:
        return Mem.ERROR_RESPONSE
    if cmd_type == Types.Action or cmd_type == Types.Read:
        return '{}\r\n\r\n{}'.format(value, Mem.OK_RESPONSE)
    if cmd_type == Types.Test:
        return '{}\r\n\r\n{}'.format(test, Mem.OK_RESPONSE)
    else:
        return Mem.ERROR_RESPONSE


def gen_response_no_action(command, cmd_type, value, test, cmd_len):
    if len(command) != cmd_len:
        return Mem.ERROR_RESPONSE
    if cmd_type == Types.Read:
        return '{}\r\n\r\n{}'.format(value, Mem.OK_RESPONSE)
    if cmd_type == Types.Test:
        return '{}\r\n\r\n{}'.format(test, Mem.OK_RESPONSE)
    else:
        return Mem.ERROR_RESPONSE


def array_response(command, cmd_type, arr_value):
    if len(command) != 2:
        return Mem.ERROR_RESPONSE
    if cmd_type == Types.Action:
        resp = ''
        for v in arr_value:
            resp += '{}\r\n\r\n'.format(v)
        resp += '{}'.format(Mem.OK_RESPONSE)
        return resp
    if cmd_type == Types.Test:
        return Mem.OK_RESPONSE
    else:
        return Mem.ERROR_RESPONSE


def psm_time(value, table):
    try:
        idx = int(value[:3], 2)
        timer = int(value[3:], 2)
        unit = table[idx]
        return timer * unit
    except (ValueError, KeyError):
        return -1


class SARAN210:
    run = True
    radio = False
    reg_mode = 1
    operator = 'FFFF'
    registered = False
    attached = False
    psm = False
    psm_status = 0
    psm_periodic = 0
    psm_active = 0
    psm_periodic_str = '01000001'
    psm_active_str = '00000101'
    psm_notification = 0
    conn_status = 0
    conn_notification = False
    idle_timer = 0
    reg_timer = 0
    psm_active_timer = 0
    psm_periodic_timer = 0
    cid = 0
    cereg = 0
    pdp_type = '"IP"'
    apn_name = ''
    clients = None

    def __init__(self, port, speed):
        self.comport = serial.Serial(port, speed, timeout=.2)
        start_new_thread(self.reception_loop, ())
        self.clients = udpClient.UDPClient()

    def receive_command(self):
        buffer = ''
        while True:
            if self.comport.inWaiting():
                rx_char = str(self.comport.read(), 'utf-8', errors='ignore')
                buffer += rx_char
            else:
                break

        buffer.strip('\r\n')
        print('Rx: {}'.format(buffer))
        return buffer

    def send_response(self, response):
        print('Tx: {}'.format(response))
        try:
            self.comport.write(('\r\n' + response + '\r\n').encode())
        except serial.SerialException:
            pass

    def reception_loop(self):
        while self.run:
            if self.comport.inWaiting():
                command = self.receive_command()
                self.main_switch(command)
            self.check_registration()
            self.check_idle()
            self.check_psm()
            self.check_messages()
            time.sleep(0.01)

    def stop_loop(self):
        self.run = False
        self.comport.close()

    def main_switch(self, command):
        cmd_type = Types.Action
        pattern = r'\+'
        if '=?' in command:
            cmd_type = Types.Test
            pattern = r'\+|=\?'
        elif '=' in command:
            cmd_type = Types.Set
            pattern = r'\+|='
        elif '?' in command:
            cmd_type = Types.Read
            pattern = r'\+|\?'

        command_arr = re.split(pattern, command.rstrip())
        command_arr = list(filter(None, command_arr))
        #print(command_arr)

        if command_arr[0] != 'AT':
            return self.send_response(Mem.ERROR_RESPONSE)

        switcher = {
            'CGMI': partial(self.manufacturer, command_arr, cmd_type),
            'CGMM': partial(self.model_identification, command_arr, cmd_type),
            'CGMR': partial(self.firmware_version, command_arr, cmd_type),
            'CGSN': partial(self.module_imei, command_arr, cmd_type),
            'CIMI': partial(self.module_imsi, command_arr, cmd_type),
            'CCID': partial(self.card_id, command_arr, cmd_type),
            'CLAC': partial(self.available_commands, command_arr, cmd_type),
            'CFUN': partial(self.radio_fun, command_arr, cmd_type),
            'NRB': partial(self.reboot_module, command_arr, cmd_type),
            'NUESTATS': partial(self.nue_stats, command_arr, cmd_type),
            'CSQ': partial(self.signal_quality, command_arr, cmd_type),
            'COPS': partial(self.network_operator, command_arr, cmd_type),
            'CSCON': partial(self.connection_status, command_arr, cmd_type),
            'CGDCONT': partial(self.data_context, command_arr, cmd_type),
            'CGATT': partial(self.de_attach, command_arr, cmd_type),
            'CEREG': partial(self.registration_status, command_arr, cmd_type),
            'CPSMS': partial(self.power_saving, command_arr, cmd_type),
            'NPSMR': partial(self.power_saving_notification, command_arr, cmd_type),
            'NSOCR': partial(self.create_socket, command_arr, cmd_type),
            'NSOST': partial(self.send_message, command_arr, cmd_type),
            'NSORF': partial(self.get_message, command_arr, cmd_type),
            'NSOCL': partial(self.close_socket, command_arr, cmd_type),
            'NPING': partial(self.ping_server, command_arr, cmd_type)
        }

        if len(command_arr) == 1:
            if cmd_type == Types.Action:
                return self.send_response(Mem.OK_RESPONSE)
            else:
                return self.send_response(Mem.ERROR_RESPONSE)

        func = switcher.get(command_arr[1], 'Invalid command')

        if isinstance(func, str):
            self.send_response(Mem.ERROR_RESPONSE)
        else:
            func()

    def check_registration(self):
        if self.reg_timer > 0 and time.time() - self.reg_timer > 0:
            self.registered = True
            self.conn_status = 1
            self.send_conn_notification()
            self.idle_timer = time.time() + Mem.IDLE_TIMEOUT
            self.reg_timer = 0
            self.attached = True

    def check_idle(self):
        if self.idle_timer == 0 or self.registered is False:
            return
        if time.time() - self.idle_timer > 0:
            self.conn_status = 0
            self.send_conn_notification()
            self.idle_timer = 0
            if self.psm is True:
                self.psm_active_timer = time.time() + self.psm_active
                self.psm_periodic_timer = time.time() + self.psm_periodic

    def check_psm(self):
        if self.psm_active_timer == 0 or self.psm_periodic_timer == 0:
            return
        if self.psm is True:
            change = False
            if time.time() - self.psm_active_timer > 0:
                self.psm_status = 1
                self.psm_active_timer = self.psm_periodic_timer + self.psm_active + random.randint(2, 5)
                change = True
            if time.time() - self.psm_periodic_timer > 0:
                self.psm_status = 0
                self.conn_status = 1
                self.idle_timer = time.time() + Mem.IDLE_TIMEOUT
                self.psm_periodic_timer = self.psm_active_timer - self.psm_active + self.psm_periodic + Mem.IDLE_TIMEOUT
                change = True
            if self.psm_notification == 1 and change is True:
                self.send_response('+NPSMR: {}'.format(self.psm_status))
                self.send_conn_notification()

    def send_conn_notification(self):
        if self.conn_notification == 1:
            self.send_response('+CSCON: {}'.format(self.conn_status))

    def check_messages(self):
        if self.psm_status == 1 or self.registered is False:
            return
        for k, v in self.clients.get_messages().items():
            self.send_response('+NSONMI: {}, {}'.format(k, v))
            self.send_response(Mem.OK_RESPONSE)

    def manufacturer(self, command, cmd_type):
        self.send_response(gen_response(command, cmd_type, Mem.MANUFACTURER, 2))

    def model_identification(self, command, cmd_type):
        self.send_response(gen_response(command, cmd_type, Mem.MODEL, 2))

    def firmware_version(self, command, cmd_type):
        self.send_response(array_response(command, cmd_type, Mem.FIRMWARE))

    def module_imei(self, command, cmd_type):
        if len(command) != 3:
            self.send_response(Mem.ERROR_RESPONSE)
            return

        if cmd_type == Types.Test:
            self.send_response('{}\r\n\r\n{}'.format(Mem.IMEI_TEST, Mem.OK_RESPONSE))
            return

        try:
            t = int(command[2])
        except ValueError:
            self.send_response(Mem.ERROR_RESPONSE)
            return

        if t == 1:
            self.send_response('+CGSN:{}\r\n\r\n{}'.format(Mem.IMEI, Mem.OK_RESPONSE))
            return
        if t == 2:
            self.send_response('+CGSN:{}{}\r\n\r\n{}'.format(Mem.IMEI, Mem.SV, Mem.OK_RESPONSE))
            return
        if t == 3:
            self.send_response('+CGSN:{}\r\n\r\n{}'.format(Mem.SV, Mem.OK_RESPONSE))
            return

    def module_imsi(self, command, cmd_type):
        self.send_response(gen_response(command, cmd_type, Mem.IMSI, 2))

    def card_id(self, command, cmd_type):
        self.send_response(gen_response(command, cmd_type, '+CCID:{}'.format(Mem.IMSI), 2))

    def available_commands(self, command, cmd_type):
        self.send_response(array_response(command, cmd_type, Mem.CLAC))

    def radio_fun(self, command, cmd_type):

        if cmd_type == Types.Test and len(command) == 2:
            return self.send_response('{}\r\n{}'.format(Mem.CFUN_TEST, Mem.OK_RESPONSE))

        if cmd_type == Types.Read and len(command) == 2:
            return self.send_response('+CFUN: {}\r\n{}'.format(1 if self.radio is True else 0, Mem.OK_RESPONSE))

        if len(command) == 3:
            if not (command[2] == '0' or command[2] == '1'):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            self.radio = True if command[2] == '1' else False

            if self.radio is False:
                self.registered = False
                self.attached = False
                self.reg_timer = 0
            elif self.reg_mode == 0:
                self.reg_timer = time.time() + random.randint(2, 30)

            time.sleep(1)
            self.send_response(Mem.OK_RESPONSE)
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def reboot_module(self, command, cmd_type):
        if len(command) == 2 and cmd_type == Types.Action:
            self.radio = False
            self.reg_mode = 1
            self.operator = 'FFFF'
            self.registered = False
            self.attached = False
            self.psm = False
            self.psm_status = 0
            self.psm_periodic = 0
            self.psm_active = 0
            self.psm_periodic_str = '01000001'
            self.psm_active_str = '00000101'
            self.psm_notification = 0
            self.conn_status = 0
            self.conn_notification = False
            self.idle_timer = 0
            self.reg_timer = 0
            self.psm_active_timer = 0
            self.psm_periodic_timer = 0
            self.cid = 0
            self.cereg = 0
            self.pdp_type = '"IP"'
            self.apn_name = ''
            self.clients.stop_clients()
            self.send_response('REBOOTING')
            time.sleep(3)
            self.send_response('{}{}'.format(Mem.REBOOT, Mem.OK_RESPONSE))
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def nue_stats(self, command, cmd_type):

        if len(command) == 2:
            if cmd_type == Types.Test:
                resp = 'NUESTATS: ('
                for k in Mem.STATS.keys():
                    resp += '"{}",'.format(k)
                resp += '"ALL")\r\n\r\n{}'.format(Mem.OK_RESPONSE)
                self.send_response(resp)
                return

            if cmd_type == Types.Action:
                resp = ''
                for k, v in Mem.STATS.get('RADIO').items():
                    resp += '"{}",{}\r\n'.format(k, v)
                self.send_response('{}'.format(Mem.OK_RESPONSE))
                return

        if len(command) == 3:
            if cmd_type == Types.Set:
                if command[2] == '"ALL"':
                    for k, i in Mem.STATS.items():
                        if k != 'CELL':
                            for s, v in i.items():
                                resp = 'NUESTATS: "{}","{}"{}{}'.format(k, s, ':' if k == 'APPSMEM' else ',', v)
                                self.send_response(resp)
                        else:
                            resp = 'NUESTATS: "{}"'.format(k)
                            for v in i.values():
                                resp += ',{}'.format(v)
                            self.send_response(resp)
                    self.send_response('{}'.format(Mem.OK_RESPONSE))
                    return

                if command[2] in ['"RADIO"', '"BLER"', '"THP"', '"APPSMEM"']:
                    for k, v in Mem.STATS[str(command[2]).replace('"', '')].items():
                        resp = 'NUESTATS: {},"{}"{}{}'.format(command[2], k, ':' if command[2] == '"APPSMEM"' else ',', v)
                        self.send_response(resp)
                    self.send_response('{}'.format(Mem.OK_RESPONSE))
                    return

                if command[2] == '"CELL"':
                    resp = 'NUESTATS: {}'.format(command[2])
                    for v in Mem.STATS[str(command[2]).replace('"', '')].values():
                        resp += ',{}'.format(v)
                    self.send_response(resp)
                    self.send_response('{}'.format(Mem.OK_RESPONSE))
                    return

        self.send_response(Mem.ERROR_RESPONSE)
        return

    def signal_quality(self, command, cmd_type):
        self.send_response(gen_response_test(command, cmd_type, '+CSQ: 31,0', Mem.CSQ_TEST, 2))

    def network_operator(self, command, cmd_type):
        if len(command) == 2:
            if cmd_type == Types.Read:
                self.send_response('+COPS: {},{},"{}"'.format(self.reg_mode, 2, self.operator))
                self.send_response(Mem.OK_RESPONSE)
                return

            if cmd_type == Types.Test:
                self.send_response(Mem.COPS_TEST)
                self.send_response(Mem.OK_RESPONSE)
                return

        if len(command) == 3 and cmd_type == Types.Set:
            params = command[2].split(',')

            if params[2][0] != '"' or params[2][-1] != '"':
                self.send_response(Mem.ERROR_RESPONSE)
                return

            operator = params[2].replace('"', '')

            try:
                mode = int(params[0])
                operator_format = int(params[1])
                int(operator, 16)
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= mode <= 2) or operator_format != 2:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            self.operator = operator
            self.reg_mode = mode

            if mode == 2:
                self.registered = False
                self.attached = False
            else:
                if self.radio is True:
                    self.reg_timer = time.time() + random.randint(5, 20)

            self.send_response(Mem.OK_RESPONSE)
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def connection_status(self, command, cmd_type):
        if len(command) == 2:
            self.send_response(gen_response_no_action(command, cmd_type, '+CSCON: {},{}'
                                                      .format('1' if self.conn_notification else '0', self.conn_status),
                                                      Mem.CSCON_TEST, 2))
            return

        if len(command) == 3:
            try:
                mode = int(command[2])
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= mode <= 1):
                self.send_response(Mem.ERROR_RESPONSE)
                return
            self.conn_notification = mode
            self.send_response(Mem.OK_RESPONSE)
            return

        return self.send_response(Mem.ERROR_RESPONSE)

    def data_context(self, command, cmd_type):
        if len(command) == 2:
            self.send_response(gen_response_no_action(command, cmd_type, '+CGDCONT: {},{},{},,0,0,,,,,1'
                                                      .format(self.cid, self.pdp_type, self.apn_name),
                                                      Mem.CGDCONT_TEST, 2))
            return

        if 3 <= len(command) <= 11 and cmd_type == Types.Set:
            params = command[2].split(',')
            try:
                cid = int(params[0])
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not(params[1] in ['"IP"', '"NONIP"']):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            self.cid = cid
            self.pdp_type = params[1]
            self.apn_name = params[2]
            self.send_response(Mem.OK_RESPONSE)
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def de_attach(self, command, cmd_type):
        if len(command) == 2:
            self.send_response(gen_response_no_action(command, cmd_type, '+CGATT: {}'.format(1 if self.attached else 0),
                                                      Mem.CGATT_TEST, 2))
            return

        if len(command) == 3 and cmd_type == Types.Set:
            if command[2] in ['0', '1']:
                self.attached = True if command[2] == '1' else 0
                self.send_response(Mem.OK_RESPONSE)
                return

        self.send_response(Mem.ERROR_RESPONSE)

    def registration_status(self, command, cmd_type):
        if len(command) == 2:
            if cmd_type == Types.Test:
                self.send_response(Mem.CEREG_TEST)
                return self.send_response(Mem.OK_RESPONSE)
            if cmd_type == Types.Read:
                #TODO: add multiple cereg definition
                self.send_response('+CEREG: {},{}'.format(1 if self.registered else 0, self.cereg))
                self.send_response(Mem.OK_RESPONSE)
                return

        if len(command) == 3:
            try:
                cereg = int(command[2])
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= cereg <= 5):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            self.cereg = cereg
            self.send_response(Mem.OK_RESPONSE)
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def power_saving(self, command, cmd_type):
        if len(command) == 2:
            self.send_response(gen_response_no_action(command, cmd_type, '+CPSMS: {},,,"{}","{}"'
                                                      .format(1 if self.psm is True else 0, self.psm_periodic_str,
                                                              self.psm_active_str), Mem.CPSM_TEST, 2))
            return

        if len(command) == 3:
            params = command[2].split(',')

            if not (params[0] in ['1', '0']):
                self.send_response(Mem.ERROR_RESPONSE)
                return
            self.psm_periodic_str = params[3].replace('"', '')
            self.psm_active_str = params[4].replace('"', '')
            self.psm_periodic = psm_time(self.psm_periodic_str, Mem.PSM_PERIODIC)
            self.psm_active = psm_time(self.psm_active_str, Mem.PSM_ACTIVE)
            if self.psm_periodic < 0 or self.psm_active < 0 or self.psm_periodic < self.psm_active:
                self.send_response(Mem.ERROR_RESPONSE)
                return
            self.psm = bool(params[0])
            if self.psm is False:
                self.psm_periodic_timer = 0
                self.psm_active_timer = 0
                self.psm_status = 0
            self.send_response(Mem.OK_RESPONSE)
            return
        self.send_response(Mem.ERROR_RESPONSE)

    def power_saving_notification(self, command, cmd_type):
        if len(command) == 2:
            self.send_response(gen_response_no_action(command, cmd_type, '+NPSMR: {}'.format(self.psm_notification),
                                                      Mem.NPSMR_TEST, 2))
            return

        if len(command) == 3 and cmd_type == Types.Set:
            if command[2] in ['0', '1']:
                self.psm_notification = int(command[2])
                self.send_response(Mem.OK_RESPONSE)
                return
        self.send_response(Mem.ERROR_RESPONSE)

    def create_socket(self, command, cmd_type):
        if len(command) == 3 and cmd_type == Types.Set:
            params = command[2].split(',')

            if not (3 <= len(params) <= 4):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            receive_control = 1

            if len(params) == 4 and params[3] in ['0', '1']:
                receive_control = int(params[3])

            if not (params[0] == '"DGRAM"') and not (params[1] == '17'):
                self.send_response(Mem.ERROR_RESPONSE)
                return
            try:
                port = int(params[2])
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= port <= 65535):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            client = self.clients.create_client(port, receive_control)

            if client < 0:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            self.send_response("{}".format(client))

            self.send_response(Mem.OK_RESPONSE)
            return

        self.send_response(Mem.ERROR_RESPONSE)

    def send_message(self, command, cmd_type):
        if len(command) == 3 and cmd_type == Types.Set:
            params = command[2].split(',')
            data = params[4].replace('"', '')

            if len(params) != 5:
                return self.send_response(Mem.ERROR_RESPONSE)

            try:
                socket = int(params[0])
                port = int(params[2])
                length = int(params[3])
                int(data, 16)
            except ValueError:
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= socket <= 7):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if not (0 <= port <= 65535):
                self.send_response(Mem.ERROR_RESPONSE)
                return

            if len(data)/2 != length:
                return self.send_response(Mem.ERROR_RESPONSE)

            if not (0 <= length <= 512):
                return self.send_response(Mem.ERROR_RESPONSE)

            if self.registered is False:
                return self.send_response(Mem.ERROR_RESPONSE)

            if self.conn_status == 0:
                self.conn_status = 1
                self.send_conn_notification()

            if self.psm_status == 1:
                self.psm_status = 0
                self.psm_periodic_timer = 0
                self.psm_active_timer = 0

            address = params[1].replace('"', '')

            sent = self.clients.send_send_message(data, address, port, socket)

            if sent <= 0:
                return self.send_response(Mem.ERROR_RESPONSE)

            self.idle_timer = time.time() + Mem.IDLE_TIMEOUT
            self.send_response('{},{}'.format(socket, sent))
            return self.send_response(Mem.OK_RESPONSE)

        self.send_response(Mem.ERROR_RESPONSE)

    def get_message(self, command, cmd_type):
        if len(command) == 3 and cmd_type == Types.Set:
            params = command[2].split(',')

            if len(params) != 2:
                return self.send_response(Mem.ERROR_RESPONSE)

            try:
                socket = int(params[0])
                length = int(params[1])
            except ValueError:
                return self.send_response(Mem.ERROR_RESPONSE)

            resp = self.clients.read_message(socket, length)

            if len(resp) == 0:
                return self.send_response(Mem.ERROR_RESPONSE)

            self.send_response('{},"{}",{},{},"{}",{}'.format(*resp))
            return self.send_response(Mem.OK_RESPONSE)

    def close_socket(self, command, cmd_type):
        if len(command) == 3 and cmd_type == Types.Set:
            try:
                socket = int(command[2])
            except ValueError:
                return self.send_response(Mem.ERROR_RESPONSE)

            resp = self.clients.close_client(socket)

            if resp < 0:
                return self.send_response(Mem.ERROR_RESPONSE)

            return self.send_response(Mem.OK_RESPONSE)

        self.send_response(Mem.ERROR_RESPONSE)

    def ping_server(self, command, cmd_type):
        if len(command) == 3 and cmd_type == Types.Set:
            params = command[2].split(',')
            if not(1 <= len(params) <= 3):
                return self.send_response(Mem.ERROR_RESPONSE)
            addr = params[0].replace('"', '')
            size = 8
            timeout = 10000
            if 2 <= len(params) <= 3:
                try:
                    size = int(params[1])
                except ValueError:
                    return self.send_response(Mem.ERROR_RESPONSE)

            if not (8 <= size <= 1460):
                return self.send_response(Mem.ERROR_RESPONSE)

            if len(params) == 3:
                try:
                    timeout = int(params[2])
                except ValueError:
                    return self.send_response(Mem.ERROR_RESPONSE)

            if not (10 <= timeout <= 60000):
                return self.send_response(Mem.ERROR_RESPONSE)

            self.send_response(Mem.OK_RESPONSE)

            if self.registered is False:
                return self.send_response('+NPINGERR: 2')

            resp = ping(addr, timeout=round(timeout/1000), unit='ms', size=size)

            if resp is None or resp is False:
                return self.send_response('+NPINGERR: 1')

            return self.send_response('+NPING: 1,"{}",20,{}'.format(addr, round(resp)))

        self.send_response(Mem.ERROR_RESPONSE)






