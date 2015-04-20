import logging
import uuid

from tornado.tcpclient import TCPClient
from tornado import gen

from checkio_referee.editor import packet
from checkio_referee.exceptions import EditorPacketStructureError
from checkio_referee.utils.signals import Signal


class EditorClient(object):
    """
    Client for connect Referee and server worker (send and request info).
    Protocol description: https://checkio.atlassian.net/wiki/pages/viewpage.action?pageId=18219162
    """

    TERMINATOR = b'\n'
    ATTR_NAME_CONNECTION_ID = 'user_connection_id'
    ATTR_NAME_DOCKER_ID = 'docker_id'

    def __init__(self, host, port, user_connection_id, docker_id, io_loop):
        self.__host = host
        self.__port = port
        self.__user_connection_id = user_connection_id
        self.__docker_id = docker_id
        self._io_loop = io_loop
        self.client = TCPClient(io_loop=self._io_loop)
        self._stream = None
        self._requests = dict()
        self._requests_signals = {
            packet.InPacket.METHOD_SELECT_RESULT: Signal('data'),
            packet.InPacket.METHOD_GET_STATUS: Signal('data'),
            packet.InPacket.METHOD_CANCEL: Signal('data'),
        }

    @gen.coroutine
    def connect(self):
        try:
            yield self._connect(self.__host, self.__port)
        except IOError as e:
            logging.error(e, exc_info=True)
            raise
        self._read()
        return True

    @gen.coroutine
    def _connect(self, host, port):
        self._stream = yield self.client.connect(host=host, port=port)
        self._confirm_connection()

    def set_close_callback(self, callback):
        self._stream.set_close_callback(callback)

    @gen.coroutine
    def _write(self, method, data=None, request_id=None):
        if self._stream.closed():
            raise EditorPacketStructureError('Connection is closed')

        message = packet.OutPacket(method, data, request_id).encode()
        try:
            yield self._stream.write(message + self.TERMINATOR)
        except Exception as e:
            logging.error(e, exc_info=True)
        else:
            logging.debug('EditorClient:: send: {}'.format(message))

    def _read(self):
        self._stream.read_until(self.TERMINATOR, self._on_data)

    def _on_data(self, data):
        logging.info('UserClient:: received: {}'.format(data))
        if data is None:
            logging.error("UserClient:: received")
        else:
            try:
                pkt = packet.InPacket.decode(data)
            except EditorPacketStructureError as e:
                logging.error(e, exc_info=True)
            else:
                if pkt.request_id is not None:
                    f = self._requests[pkt.request_id]
                    f.set_result(result=pkt.data)
                    del self._requests[pkt.request_id]
                signal = self._requests_signals[pkt.method]
                signal.send(data=pkt.data)
        self._read()

    def add_cancel_callback(self, callback):
        self.add_data_callback(packet.InPacket.METHOD_CANCEL, callback)

    def add_data_callback(self, request_method, callback):
        if request_method not in self._requests_signals.keys():
            raise Exception('Undefined request method {}'.format(request_method))

        signal = self._requests_signals[request_method]
        signal.connect(callback)

    def send_select_data(self, data):
        request_id = uuid.uuid4().hex
        self._write(packet.OutPacket.METHOD_SELECT, data, request_id)
        self._requests[request_id] = gen.Future()
        return self._requests[request_id]

    @gen.coroutine
    def send_stderr(self, line):
        yield self._write(packet.OutPacket.METHOD_STDERR, line)

    @gen.coroutine
    def send_stdout(self, line):
        yield self._write(packet.OutPacket.METHOD_STDOUT, line)

    @gen.coroutine
    def send_check_result(self, success, code, points=None, additional_data=None):
        yield self.send_result(
            action=packet.RESULT_ACTION_CHECK,
            success=success,
            code=code,
            points=points,
            additional_data=additional_data
        )

    @gen.coroutine
    def send_try_it_result(self, success, code, points=None, additional_data=None):
        yield self.send_result(
            action=packet.RESULT_ACTION_TRY_IT,
            success=success,
            code=code,
            points=points,
            additional_data=additional_data
        )

    @gen.coroutine
    def send_run_finish(self, code):
        yield self.send_result(action=packet.RESULT_ACTION_RUN, success=True, code=code)

    @gen.coroutine
    def send_pre_test(self, data):
        yield self._write(packet.OutPacket.METHOD_PRE_TEST, data)

    @gen.coroutine
    def send_post_test(self, data):
        yield self._write(packet.OutPacket.METHOD_POST_TEST, data)

    @gen.coroutine
    def send_result(self, action, success, code, points=None, additional_data=None):
        if action not in (packet.RESULT_ACTION_CHECK, packet.RESULT_ACTION_TRY_IT,
                          packet.RESULT_ACTION_RUN):
            raise EditorPacketStructureError(
                'REFEREE:: Sent to editor action is incorrect: {}'.format(action))
        data = {
            'action': action,
            'success': bool(success),
            'code': code,
        }
        if points is not None:
            data['points'] = points
        if additional_data is not None:
            data['additional_data'] = additional_data
        yield self._write(packet.OutPacket.METHOD_RESULT, data)

    @gen.coroutine
    def send_error(self, message, traceback=None):
        data = {
            'message': message
        }
        if traceback is not None:
            data['traceback'] = traceback
        yield self._write(packet.OutPacket.METHOD_ERROR, data)

    @gen.coroutine
    def send_status(self, status_data):
        yield self._write(packet.OutPacket.METHOD_STATUS, status_data)

    @gen.coroutine
    def send_custom(self, data):
        yield self._write(packet.OutPacket.METHOD_CUSTOM, data)

    @gen.coroutine
    def _confirm_connection(self):
        """
        Only after client send connection id, server will start send data.
        Until that, server will skipp all requests.
        """
        yield self._write(packet.OutPacket.METHOD_SET, {
            self.ATTR_NAME_CONNECTION_ID: self.__user_connection_id,
            self.ATTR_NAME_DOCKER_ID: self.__docker_id
        })
