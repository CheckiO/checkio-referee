import os
import logging
from functools import partial

from tornado import gen
from tornado.concurrent import Future
from tornado.process import Subprocess

from .exceptions import ExecutorException
from .tcpserver import ExecutorTCPServer


class ExecutorController(object):

    DEFAULT_ENV_NAME = "__CHECKIO_ENV__"
    CHECK_OUTPUT_DELAY = 500
    EXECUTABLE_FILE_NAME = 'run.sh'

    def __init__(self, io_loop, executable_path, referee):
        self.io_loop = io_loop
        self.executable_path = executable_path
        self.referee = referee

        self.current_exec_name = None
        self.connections = None
        self.connected = {}

        self.server = ExecutorTCPServer(controller=self, io_loop=io_loop)
        self.server.listen(ExecutorTCPServer.PORT)

    def set_current_exec(self, exec_name):
        self.current_exec_name = exec_name

    def _get_connection(self, exec_name=None):
        if exec_name is None:
            exec_name = self.current_exec_name
        if exec_name is None:
            raise ExecutorException('No env name is passed')
        if self.connections is None:
            raise ExecutorException('No connections')
        if exec_name not in self.connections:
            raise ExecutorException('No connection with env name `{}`'.format(exec_name))

        return self.connections[exec_name]

    @gen.coroutine
    def _write(self, data, exec_name=None):
        connection = self._get_connection(exec_name)
        yield connection.write(data)

    @gen.coroutine
    def _request(self, data, exec_name=None):
        connection = self._get_connection(exec_name)
        yield connection.write(data)
        return (yield connection.read_message())

    def on_connection_message(self, data, stream):
        if data.get('status') != 'connected':
            raise ExecutorException("Wrong connection message {}".format(str(data)))
        exec_name = data['exec_name']
        try:
            self.connections[exec_name] = stream
        except TypeError:
            self.connections = {
                exec_name: stream
            }
        self.connected[exec_name].set_result(True)

    def start_env(self, exec_name=None, config=None):
        if exec_name is None:
            exec_name = self.DEFAULT_ENV_NAME
            self.current_exec_name = self.DEFAULT_ENV_NAME

        if self.connections is not None and exec_name in self.connections.keys():
            raise ExecutorException('Env {} already exists'.format(exec_name))

        executable = os.path.join(self.executable_path, self.EXECUTABLE_FILE_NAME)
        args = [
            executable,  # TODO: WTF
            str(ExecutorTCPServer.PORT),
            exec_name
        ]
        stream = Subprocess.STREAM
        env = {'PYTHONUNBUFFERED': '0'}
        try:
            sub_process = Subprocess(args=args, executable=executable, stdout=stream,
                                     stderr=stream, env=env)
        except Exception as e:
            logging.error(e)
            raise

        on_stdout = partial(self.referee.on_stdout, exec_name)
        on_stderr = partial(self.referee.on_stderr, exec_name)
        read_lines(exec_name, sub_process.stdout, on_stdout)
        read_lines(exec_name, sub_process.stderr, on_stderr)

        self.connected[exec_name] = Future()
        return self.connected[exec_name]

    @gen.coroutine
    def run_code(self, code, exec_name=None):
        result = yield self._request({
            'action': 'run_code',
            'code': code,
        }, exec_name)
        return result

    @gen.coroutine
    def run_func(self, function_name, args, exec_name=None):
        result = yield self._request({
            'action': 'run_function',
            'function_name': function_name,
            'function_args': args
        }, exec_name)
        return result

    @gen.coroutine
    def run_code_and_function(self, code, function_name, args, exec_name=None):
        data = yield self._request({
            'action': 'run_code_and_function',
            'code': code,
            'function_name': function_name,
            'function_args': args
        }, exec_name)
        if data.get('status') == 'success':
            return data.get('result')

    @gen.coroutine
    def run_in_console(self, code, exec_name=None):
        result = yield self._request({
            'action': 'run_in_console',
            'code': code,
        }, exec_name)
        return result

    @gen.coroutine
    def set_config(self, env_config, exec_name=None):
        result = yield self._request({
            'action': 'config',
            'env_config': env_config
        }, exec_name)
        return result

    @gen.coroutine
    def kill(self, exec_name=None):
        result = yield self._write({
            'action': 'kill'
        }, exec_name)
        return result

    @gen.coroutine
    def kill_all(self):
        kill_connections = []
        for exec_name in self.connections.keys():
            kill_connections.append(self._write({
                'action': 'kill'
            }, exec_name))
        return (yield kill_connections)


def read_lines(exec_name, stream, data_callback, line=None):
    if stream.closed():
        return
    if line is not None:
        data_callback(line.decode().strip())
    read_callback = partial(read_lines, exec_name, stream, data_callback)
    stream.read_until(b'\n', read_callback)
