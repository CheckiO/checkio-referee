import logging
import uuid
from functools import partial

from tornado import gen
from tornado.concurrent import Future
from tornado.process import Subprocess

from checkio_referee.exceptions import CheckioEnvironmentError
from checkio_referee.environment.tcpserver import EnvironmentsTCPServer
from checkio_referee.environment.client import EnvironmentClient

logger = logging.getLogger(__name__)


class EnvironmentsController(object):

    ENVIRONMENT_CLIENT_CLS = EnvironmentClient

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
            logger.error(e)
            raise

        def decode_data(func):
            def _decode(data):
                return func(data.decode('utf-8'))
            return _decode
        _on_stdout = decode_data(partial(on_stdout, environment_id))
        _on_stderr = decode_data(partial(on_stderr, environment_id))
        sub_process.stdout.read_until_close(lambda a: a, streaming_callback=_on_stdout)
        sub_process.stderr.read_until_close(lambda a: a, streaming_callback=_on_stderr)
        self._connections[environment_id] = Future()
        return self._connections[environment_id]

    def on_connection_message(self, data, stream):
        if data.get('status') != 'connected':
            raise CheckioEnvironmentError("Wrong connection message {}".format(str(data)))
        environment_id = data['environment_id']
        environment_client = self.ENVIRONMENT_CLIENT_CLS(stream, environment_id)
        environment_client.set_on_stop_callback(self.on_environment_stopped)
        logger.debug("EnvironmentsController:: connected {}".format(environment_id))
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
