import logging

from tornado import gen
from tornado.ioloop import IOLoop

logger = logging.getLogger(__name__)


class BaseHandler(object):

    def __init__(self, env_name, code, editor_client, environments_controller):
        self.env_name = env_name
        self.code = code
        self.editor_client = editor_client
        self._environments_controller = environments_controller

        self.environment = None
        self._is_stopping = None
        self._stop_callback = None

    @gen.coroutine
    def start(self):
        raise NotImplementedError

    def add_stop_callback(self, callback):
        self._stop_callback = callback

    def stop(self):
        if self._is_stopping is not None:
            return
        self._is_stopping = True
        if self._stop_callback is not None:
            self._stop_callback()

        if self.environment is not None:
            self.environment.stop()

    @gen.coroutine
    def get_environment(self, env_name):
        environment = yield self._environments_controller.get_environment(
            env_name, on_stdout=self.on_stdout, on_stderr=self.on_stderr)
        return environment

    def on_stdout(self, exec_name, line):
        logging.debug("STDOUT: " + line)
        IOLoop.current().spawn_callback(self.editor_client.send_stdout, line)

    def on_stderr(self, exec_name, line):
        logging.debug("STDERR: " + line)
        IOLoop.current().spawn_callback(self.editor_client.send_stderr, line)
