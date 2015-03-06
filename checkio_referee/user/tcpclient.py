import logging

from tornado.tcpclient import TCPClient
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.escape import json_encode, json_decode


class UserClient(object):
    """
    Client for connect Referee and server worker (send and request info).
    Protocol description: https://checkio.atlassian.net/wiki/pages/viewpage.action?pageId=18219162
    """

    terminator = b'\n'
    ATTR_NAME_CONNECTION_ID = 'user_connection_id'

    def __init__(self, host, port, user_connection_id, io_loop=None):
        self.__host = host
        self.__port = port
        self.__user_connection_id = user_connection_id
        self._io_loop = io_loop or IOLoop.current()
        self.client = TCPClient(io_loop=self._io_loop)
        self.stream = None

    @gen.coroutine
    def connect(self):
        try:
            return (yield self._connect(self.__host, self.__port))
        except IOError as e:
            logging.error(e, exc_info=True)
            raise

    @gen.coroutine
    def _connect(self, host, port):
        self.stream = yield self.client.connect(host=host, port=port)
        self.__set_user_connection_id()
        return True

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
        logging.info('UserClient:: send: {}'.format(message))

    @gen.coroutine
    def _read(self):
        data_source = yield self.stream.read_until(self.terminator)
        logging.info('UserClient:: received: {}'.format(data_source))
        return self._data_decode(data_source)

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
    def post_check_fail(self, points=None, description=None):
        yield self.post_data({
            'type': 'check_fail',
            'points': points,
            'content': description
        })

    @gen.coroutine
    def post_check_success(self, points=None, description=None):
        yield self.post_data({
            'type': 'check_success',
            'points': points,
            'content': description
        })

    @gen.coroutine
    def __set_user_connection_id(self):
        yield self._write('set', {
            self.ATTR_NAME_CONNECTION_ID: self.__user_connection_id
        })
