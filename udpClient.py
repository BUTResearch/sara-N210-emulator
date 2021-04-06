
import socket
from _thread import *


class UDPClient:
    max_clients = 7
    run = True
    clients = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}}
    new_messages = {}

    def __init__(self):
        start_new_thread(self.reception_loop, ())

    def reception_loop(self):
        while self.run:
            for k, v in self.clients.items():
                if len(v) == 0:
                    continue
                try:
                    data, addr = v['client'].recvfrom(512)
                except socket.error:
                    pass
                else:
                    v['buff'] = data
                    v['len'] = len(data)
                    v['addr'] = addr
                    if v['notify'] == 1:
                        self.new_messages[k] = len(data)

    def create_client(self, port, rec_control):
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            client.bind(('127.0.0.1', port))
            client.setblocking(False)
        except socket.error:
            return -1
        c = {'client': client, 'notify': rec_control, 'port': port, 'len': 0, 'buff': b'', 'addr': b''}
        for k, v in self.clients.items():
            if len(v) == 0:
                self.clients[k] = c
                return k
        return -1

    def remove_client(self, idx):
        c = self.clients[idx]
        c['client'].close()
        self.clients[idx] = {}

    def get_messages(self):
        messages = self.new_messages.copy()
        self.new_messages.clear()
        return messages

    def send_send_message(self, data, address, port, idx):
        try:
            c = self.clients[idx]
            return c['client'].sendto(bytearray.fromhex(data), (address, port))
        except (socket.error, KeyError):
            return -1

    def read_message(self, idx, length):
        try:
            c = self.clients[idx]
        except KeyError:
            return []

        if c['len'] == 0:
            return []

        data_l = c['len'] if c['len'] <= length else length
        rem_l = c['len'] - data_l
        data = ''.join(format(x, '02x') for x in c['buff'][:data_l])
        c['buff'] = c['buff'][data_l:]
        c['len'] = rem_l
        addr = c['addr'][0]
        port = c['addr'][1]
        return [idx, addr, port, data_l, data, rem_l]

    def exit_clients(self):
        self.run = False
        self.stop_clients()

    def close_client(self, idx):
        c = self.clients[idx]
        if len(c) == 0:
            return -1
        c['client'].close()
        self.clients[idx] = {}
        return idx

    def stop_clients(self):
        for c in self.clients.values():
            if len(c) == 0:
                continue
            c['client'].close()
        self.clients = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}}
