import logging

from tornado import gen
from tornado.ioloop import IOLoop

from checkio_referee.user import UserClient
from checkio_referee.executor import ExecutorController
from checkio_referee.validators import EqualValidator
from checkio_referee import representations


class RefereeBase(object):
    EXECUTABLE_PATH = None
    TESTS = None
    FUNCTION_NAME = 'checkio'
    CURRENT_ENV = None
    ENV_COVERCODE = None
    VALIDATOR = EqualValidator
    CALLED_REPRESENTATIONS = {}

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

    def get_env_config(self, random_seed=None):
        env_config = {}
        if self.ENV_COVERCODE is not None and self.ENV_COVERCODE[self.CURRENT_ENV] is not None:
            env_config['cover_code'] = self.ENV_COVERCODE[self.CURRENT_ENV]
        if random_seed is not None:
            env_config['random_seed'] = random_seed
        return env_config

    @gen.coroutine
    def run(self):
        yield self.executor.start_env()
        yield self.executor.set_config(self.get_env_config())
        yield self.executor.run_code(code=self.user_data['code'])
        yield self.executor.kill()

    @gen.coroutine
    def run_in_console(self):
        yield self.executor.start_env()
        yield self.executor.set_config(self.get_env_config())
        yield self.executor.run_in_console(code=self.user_data['code'])
        # TODO: what next? kill exec?

    @gen.coroutine
    def pre_test(self, test, **kwargs):
        representation = self.CALLED_REPRESENTATIONS.get(self.CURRENT_ENV,
                                                         representations.base_representation)
        called_str = representation(test, self.FUNCTION_NAME)
        logging.info("REFEREE:: Called: {}".format(called_str))
        # TODO: Send data to Editor

    @gen.coroutine
    def post_test(self, test, validator_result, **kwargs):
        logging.info("REFEREE:: check result for category {0}, test {1}: {2}".format(
            kwargs.get("category_name", ""),
            kwargs.get("test_number", 0),
            validator_result.test_passed))
        if validator_result.additional_data:
            logging.info("VALIDATOR:: Data: {}".format(validator_result.additional_data))
        # TODO: Send data to Editor

    @gen.coroutine
    def check(self):
        """
        Run code with different arguments from self.TESTS
        :return:
        """
        logging.info("Start check")
        assert self.TESTS

        for category_name, tests in self.TESTS.items():
            yield self.executor.start_env(category_name)
            yield self.executor.set_config(self.get_env_config())
            for test_number, test in enumerate(tests):
                self.pre_test(test)
                result_code = yield self.executor.run_code_and_function(
                    code=self.user_data['code'],
                    function_name=self.FUNCTION_NAME or test["function_name"],
                    args=test.get('input', None),
                    exec_name=category_name)

                validator = self.VALIDATOR(test)
                validator_result = validator.validate(result_code)

                self.post_test(test, validator_result,
                               category_name=category_name, test_number=test_number)

                if not validator_result.test_passed:
                    yield self.executor.kill(category_name)
                    description = "Category: {0}. Test {1}".format(category_name, test_number)
                    return (yield self.user.post_check_fail(description))

            yield self.executor.kill(category_name)
        return self.check_success()

    @gen.coroutine
    def check_success(self, description=None, points=None):
        return (yield self.user.post_check_success(description=description, points=points))

    def on_stdout(self, exec_name, line):
        self.user.post_out(line)

    def on_stderr(self, exec_name, line):
        self.user.post_error(line)
