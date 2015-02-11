import logging

from tornado.tcpclient import TCPClient
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.escape import json_encode, json_decode


class UserClient(object):
    """
    Client for connect Referee and server worker (send and request info).
    Protocol description
    Request object is encoded json object:
    {
        "method": "get|post",  # required argument
        "data": None  # not required arguments
    }
    """

    terminator = b'\n'

    def __init__(self, controller, io_loop=None):
        self.controller = controller
        self.io_loop = io_loop or IOLoop.current()
        self.client = TCPClient(io_loop=self.io_loop)
        self.stream = None

    @gen.coroutine
    def connect(self, host, port):
        try:
            self.stream = yield self.client.connect(host=host, port=port)
            return True
        except IOError as e:
            logging.error(e)

    def set_close_callback(self, callback):
        self.stream.set_close_callback(callback)

    @gen.coroutine
    def _write(self, method, data):
        if self.stream is None:
            logging.warning("Bad connection")
        message = self._data_encode({
            "method": method,
            "data": data
        })
        yield self.stream.write(message)
        self._on_write(message)

    @gen.coroutine
    def _read(self):
        data_source = yield self.stream.read_until(self.terminator)
        return self._data_decode(data_source)

    def _on_write(self, message):
        logging.info('UserClient:: Message `{}` has been send'.format(message))

    def _on_read(self, message):
        logging.info('UserClient:: Message `{}` has been received'.format(message))

    def _data_encode(self, data):
        data = json_encode(data).encode()
        return data + self.terminator

    def _data_decode(self, data):
        data = data.decode('utf-8')
        if data is None:
            return
        data = json_decode(data)
        try:
            return data['data']
        except KeyError:
            return data

    @gen.coroutine
    def get_data(self, data):
        yield self._write('get', data)
        return (yield self._read())

    @gen.coroutine
    def post_data(self, data):
        yield self._write('post', data)

    @gen.coroutine
    def post_out(self, content):
        logging.info("POST OUT: {}".format(content))
        yield self.post_data({
            'type': 'out',
            'content': content
        })

    @gen.coroutine
    def post_error(self, content):
        logging.info("ERR OUT: {}".format(content))
        yield self.post_data({
            'type': 'error',
            'content': content
        })

    @gen.coroutine
    def post_check_fail(self, description=None):
        yield self.post_data({
            'type': 'check_fail',
            'content': description
        })

    @gen.coroutine
    def post_check_success(self, description=None):
        yield self.post_data({
            'type': 'check_success',
            'content': description
        })
