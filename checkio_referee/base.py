import logging

from tornado import gen
from tornado.ioloop import IOLoop

from checkio_referee.user import UserClient
from checkio_referee.executor import ExecutorController


class RefereeBase(object):

    EXECUTABLE_PATH = None
    TESTS = None
    FUNCTION_NAME = 'checkio'
    CURRENT_ENV = None
    ENV_COVERCODE = None

    def __init__(self, data_server_host, data_server_port, io_loop=None):
        assert self.EXECUTABLE_PATH
        self.tcp_server_host = data_server_host
        self.tcp_server_port = data_server_port
        self.io_loop = io_loop or IOLoop.instance()
        self.initialize()
        self.user_data = None

        self.executor = ExecutorController(self.io_loop, self.EXECUTABLE_PATH, self)
        self.user = UserClient(self.io_loop)
        self.user_connected = None
        if io_loop is None:
            IOLoop.instance().start()

    def initialize(self):
        pass

    def result_comparator(self, reference, result):
        return reference == result

    @gen.coroutine
    def start(self):
        self.user_connected = yield self.user.connect(self.tcp_server_host, self.tcp_server_port)
        self.user.set_close_callback(self.on_close_user_connection)
        if self.user_connected:
            try:
                yield self.on_ready()
            except Exception as e:
                logging.error(e)
                raise

    def on_close_user_connection(self):
        self.executor.kill_all()

    @gen.coroutine
    def on_ready(self):
        self.user_data = yield self.user.get_data(data=['code', 'user_action'])
        user_action = self.user_data['user_action']
        return {
            'run': self.run,
            'check': self.check,
            'run_in_console': self.run_in_console
        }[user_action]()

    @gen.coroutine
    def run(self):
        yield self.executor.start_env()
        yield self.executor.run_code(code=self.user_data['code'])
        yield self.executor.kill()

    @gen.coroutine
    def run_in_console(self):
        yield self.executor.start_env()
        yield self.executor.run_in_console(code=self.user_data['code'])
        # TODO: what next? kill exec?

    @gen.coroutine
    def check(self):
        """
        Run code with different arguments from self.TESTS
        :return:
        """
        logging.info("Start check")
        assert self.TESTS

        for category, tests in self.TESTS.items():
            yield self.executor.start_env(category)
            for test in tests:
                result_code = yield self.executor.run_code_and_function(
                    code=self.user_data['code'],
                    function_name=self.FUNCTION_NAME,
                    args=test['input'],
                    exec_name=category
                )
                result_compare = self.result_comparator(test['answer'], result_code)
                logging.info("REFEREE:: check result for category {0}, test {1}: {2}".format(
                    category, tests.index(test), result_compare)
                )

                if not result_compare:
                    yield self.executor.kill(category)
                    description = "Category: {0}. Test {1}".format(category, tests.index(test))
                    return (yield self.user.post_check_fail(description))
            yield self.executor.kill(category)
        return (yield self.user.post_check_success())

    def on_stdout(self, exec_name, line):
        self.user.post_out(line)

    def on_stderr(self, exec_name, line):
        self.user.post_error(line)
