import logging
import sys
import traceback
from copy import deepcopy

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

    EDITOR_LOAD_ARGS = ('code', 'action', 'env_name')

    def __init__(self, server_host, server_port, user_connection_id, docker_id, io_loop=None):
        assert self.ENVIRONMENTS
        self.__user_connection_id = user_connection_id
        self.__docker_id = docker_id
        self.__io_loop = io_loop or IOLoop.current()

        self.editor_client = EditorClient(server_host, server_port, user_connection_id, docker_id,
                                          self.__io_loop)

        self.editor_client.add_cancel_callback(self._stop_signal_receiver)
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
            self.editor_client.send_error(str(e), traceback=traceback.format_exc())
            self.stop()

    def on_close_user_connection(self):
        self.stop()

    @gen.coroutine
    def on_ready(self):
        editor_data = yield self.editor_client.send_select_data(self.EDITOR_LOAD_ARGS)
        logger.debug("Initial editor data {}".format(editor_data))

        action = editor_data['action']
        HandlerClass = self.HANDLERS.get(action)
        if HandlerClass is None:
            raise Exception("Handler for action {} is not available".format(action))

        self._handler = HandlerClass(editor_data, self.editor_client, self)
        self._handler.add_stop_callback(self.stop)
        yield self._handler.start()

    @property
    def environments_controller(self):
        if not hasattr(self, '_environments_controller'):
            setattr(self, '_environments_controller', EnvironmentsController(self.ENVIRONMENTS))
        return getattr(self, '_environments_controller')

    def stop(self):
        if self._handler is not None:
            self._handler.stop()
        sys.exit()

    def _stop_signal_receiver(self, signal, data=None):
        self.stop()


class RefereeCodeGolf(RefereeBase):
    HANDLERS = deepcopy(RefereeBase.HANDLERS)
RefereeCodeGolf.set_handler(RefereeBase.HANDLER_ACTION_CHECK, golf.CodeGolfCheckHandler)


class RefereeRank(RefereeBase):
    HANDLERS = deepcopy(RefereeBase.HANDLERS)
RefereeRank.set_handler(RefereeBase.HANDLER_ACTION_CHECK, rank.RankCheckHandler)
