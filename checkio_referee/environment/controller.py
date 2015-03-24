import os
import logging
import uuid
from functools import partial

from tornado import gen
from tornado.concurrent import Future
from tornado.process import Subprocess

from checkio_referee.exceptions import CheckioEnvironmentError
from checkio_referee.environment.tcpserver import EnvironmentsTCPServer
from checkio_referee.environment.client import EnvironmentClient


class SingletonDecorator:
    def __init__(self, cls):
        self.cls = cls
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
        return self.instance


@SingletonDecorator
class EnvironmentsController(object):

    def __init__(self, environments):
        self.environments = environments
        self._connections = {}

        self.server = EnvironmentsTCPServer()
        self.server.set_connection_message_callback(self.on_connection_message)
        self.server.listen(self.server.PORT)

    def get_environment(self, env_name, on_stdout, on_stderr):
        executable_path = self.get_executable_path(env_name)
        return self.start_env(executable_path, on_stdout, on_stderr)

    def get_executable_path(self, env_name):
        return self.environments[env_name]

    def start_env(self, executable, on_stdout, on_stderr):
        environment_id = uuid.uuid4().hex
        args = [
            executable,
            str(self.server.PORT),
            environment_id
        ]
        stream = Subprocess.STREAM
        env = {'PYTHONUNBUFFERED': '0'}
        try:
            sub_process = Subprocess(args=args, executable=executable, stdout=stream,
                                     stderr=stream, env=env)
        except Exception as e:
            logging.error(e)
            raise

        _on_stdout = partial(on_stdout, environment_id)
        _on_stderr = partial(on_stderr, environment_id)
        read_lines(environment_id, sub_process.stdout, _on_stdout)
        read_lines(environment_id, sub_process.stderr, _on_stderr)

        self._connections[environment_id] = Future()
        return self._connections[environment_id]

    def on_connection_message(self, data, stream):
        if data.get('status') != 'connected':
            raise CheckioEnvironmentError("Wrong connection message {}".format(str(data)))
        environment_id = data['environment_id']
        environment_client = EnvironmentClient(stream, environment_id)
        environment_client.set_on_stop_callback(self.on_environment_stopped)
        logging.info("EnvironmentsController:: connected {}".format(environment_id))
        self._connections[environment_id].set_result(environment_client)

    def on_environment_stopped(self, environment_id):
        del self._connections[environment_id]

    @gen.coroutine
    def stop_all_environments(self):
        stop_environments = []
        for environment in self._connections.values():
            stop_environments.append(environment.stop())
        return (yield stop_environments)

    def is_valid_env(self, env_name):
        return env_name in self.environments


def read_lines(exec_name, stream, data_callback, line=None):
    if stream.closed():
        return
    if line is not None:
        data_callback(line.decode().strip())
    read_callback = partial(read_lines, exec_name, stream, data_callback)
    stream.read_until(b'\n', read_callback)
