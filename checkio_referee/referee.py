import logging
import sys

from tornado import gen
from tornado.ioloop import IOLoop

from checkio_referee.handlers import common, golf, rank
from checkio_referee.editor import EditorClient
from checkio_referee.environment import EnvironmentsController

logger = logging.getLogger(__name__)


class RefereeBase(object):

    ENVIRONMENTS = None

    HANDLER_ACTION_RUN = 'run'
    HANDLER_ACTION_CHECK = 'check'
    HANDLER_ACTION_TRY_IT = 'try_it'
    HANDLER_ACTION_RUN_IN_CONSOLE = 'run_in_console'

    HANDLERS = {
        HANDLER_ACTION_RUN: common.RunHandler,
        HANDLER_ACTION_CHECK: common.CheckHandler,
        # HANDLER_ACTION_TRY_IT: common.TryItHandler,  # TODO:
        HANDLER_ACTION_RUN_IN_CONSOLE: common.RunInConsoleHandler,
    }

    AVAILABLE_HANDLER_ACTIONS = (HANDLER_ACTION_RUN, HANDLER_ACTION_CHECK, HANDLER_ACTION_TRY_IT,
                                 HANDLER_ACTION_RUN_IN_CONSOLE)

    def __init__(self, server_host, server_port, user_connection_id, docker_id, io_loop=None):
        assert self.ENVIRONMENTS
        self.__user_connection_id = user_connection_id
        self.__docker_id = docker_id
        self.__io_loop = io_loop or IOLoop.current()

        self.editor_client = EditorClient(server_host, server_port, user_connection_id, docker_id,
                                          self.__io_loop)
        self.editor_connected = None
        self._handler = None

        if io_loop is None:
            self.__io_loop.start()

    @classmethod
    def set_handler(cls, action, handler):
        if action not in cls.AVAILABLE_HANDLER_ACTIONS:
            raise Exception("Action {} is not available")
        try:
            cls.HANDLERS[action] = handler
        except TypeError:
            cls.HANDLERS = {
                action: handler
            }

    @gen.coroutine
    def start(self):
        self.editor_connected = yield self.editor_client.connect()
        if not self.editor_connected:
            raise Exception("Bad connecting to editor server")
        self.editor_client.set_close_callback(self.on_close_user_connection)
        try:
            yield self.on_ready()
        except Exception as e:
            logger.error(e, exc_info=True)
            self.editor_client.send_error(e, traceback=sys.exc_info())
            self.stop()

    def on_close_user_connection(self):
        self.stop()

    @gen.coroutine
    def on_ready(self):
        editor_data = yield self.editor_client.send_select_data(['code', 'action', 'env_name'])
        logger.debug("Initial editor data {}".format(editor_data))

        action = editor_data['action']
        HandlerClass = self.HANDLERS.get(action)
        if HandlerClass is None:
            raise Exception("Handler for action {} is not available")

        env_name = editor_data.get('env_name')
        if not self.environments_controller.is_valid_env(env_name):
            raise Exception("Environment {} is not supported in this mission")

        code = editor_data.get('code')
        self._handler = HandlerClass(env_name, code, self.editor_client, self)
        self._handler.add_stop_callback(self.stop)
        yield self._handler.start()
        
    @property
    def environments_controller(self):
        return EnvironmentsController(self.ENVIRONMENTS)

    def stop(self):
        if self._handler is not None:
            self._handler.stop()
        sys.exit()


class RefereeCodeGolf(RefereeBase):
    pass
RefereeCodeGolf.set_handler(RefereeBase.HANDLER_ACTION_CHECK, golf.CodeGolfCheckHandler)


class RefereeRank(RefereeBase):
    pass
RefereeRank.set_handler(RefereeBase.HANDLER_ACTION_CHECK, rank.RankCheckHandler)
