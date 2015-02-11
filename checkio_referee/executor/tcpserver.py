import logging

from tornado import gen
from tornado.escape import json_encode, json_decode
from tornado.tcpserver import TCPServer


class ExecutorTCPServer(TCPServer):

    PORT = 8383  # TODO: to settings

    def __init__(self, controller,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller
        self.stream_handler = None

    def handle_stream(self, stream, address):
        self.stream_handler = StreamHandler(stream, address, self.controller)


class StreamHandler(object):

    terminator = b'\0'

    def __init__(self, stream, address, controller):
        self.stream = stream
        self.address = address
        self.controller = controller
        self._is_connection_closed = False
        self.stream.set_close_callback(self._on_client_connection_close)
        self._read_connection_message()

    def _data_decode(self, data):
        if self.terminator in data:
            data = data.split(self.terminator)[0]
        return json_decode(data.decode())

    def _data_encode(self, data):
        data = json_encode(data)
        return data.encode('utf-8')

    def _on_client_connection_close(self):
        self._is_connection_closed = True
        logging.debug("[EXECUTOR-SERVER] :: Client at address {} has closed the connection".format(
            self.address
        ))

    @gen.coroutine
    def read_message(self):
        data = yield self.stream.read_until(self.terminator)
        return self._data_decode(data)

    def _read_connection_message(self):
        self.stream.read_until(self.terminator, self._on_connection_message)

    def _on_connection_message(self, data):
        data = self._data_decode(data)
        self.controller.on_connection_message(data, self)

    @gen.coroutine
    def write(self, message):
        if self._is_connection_closed:
            return
        message = self._data_encode(message)
        logging.debug("[EXECUTOR-SERVER] :: Message to executor {}".format(message))
        try:
            yield self.stream.write(message + self.terminator)
        except Exception as e:
            logging.error(e)
