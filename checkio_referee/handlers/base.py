import logging

from tornado import gen
from tornado.ioloop import IOLoop

logger = logging.getLogger(__name__)


class BaseHandler(object):

    REFEREE_SETTINGS_PRIORITY = None

    def __init__(self, editor_data, editor_client, referee):
        self.env_name = editor_data.get('env_name')
        if not referee.environments_controller.is_valid_env(self.env_name):
            raise Exception("Environment {} is not supported in this mission".format(
                self.env_name))

        self.code = editor_data.get('code')
        self.editor_client = editor_client
        self._referee = referee

        self.environment = None
        self._is_stopping = None
        self._stop_callback = None

    def __getattribute__(self, attr):
        referee_priority = object.__getattribute__(self, 'REFEREE_SETTINGS_PRIORITY')
        if referee_priority is not None and attr in referee_priority:
            referee_value = getattr(self._referee, attr, None)
            if referee_value is not None:
                return referee_value
        return object.__getattribute__(self, attr)

    def __getattr__(self, attr):
        if attr == attr.upper():
            return getattr(self._referee, attr)
        try:
            return super().__getattr__()
        except AttributeError as error:
            if error.args[0] == "'super' object has no attribute '__getattr__'":
                raise AttributeError('Object {} does not have attribute {}'. format(self, attr))
            else:
                raise

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
        environment = yield self._referee.environments_controller.get_environment(
            env_name, on_stdout=self.on_stdout, on_stderr=self.on_stderr)
        return environment

    def on_stdout(self, exec_name, line):
        logging.debug("STDOUT: " + line)
        IOLoop.current().spawn_callback(self.editor_client.send_stdout, line)

    def on_stderr(self, exec_name, line):
        logging.debug("STDERR: " + line)
        IOLoop.current().spawn_callback(self.editor_client.send_stderr, line)
