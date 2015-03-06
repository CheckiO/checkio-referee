import logging
import sys

from tornado import gen
from tornado.ioloop import IOLoop

from checkio_referee import exceptions
from checkio_referee.executor import ExecutorController
from checkio_referee.utils import representations, validators
from checkio_referee.user import UserClient, packet


logger = logging.getLogger(__name__)


class RefereeBase(object):
    EXECUTABLE_PATH = None
    TESTS = None
    FUNCTION_NAME = 'checkio'
    CURRENT_ENV = None
    ENV_COVERCODE = None
    VALIDATOR = validators.EqualValidator
    CALLED_REPRESENTATIONS = {}
    EXEC_NAME_RUN_IN_CONSOLE = 'run_in_console'

    def __init__(self, server_host, server_port, user_connection_id, docker_id, io_loop=None):
        assert self.EXECUTABLE_PATH
        self.__user_connection_id = user_connection_id
        self.__docker_id = docker_id
        self.__io_loop = io_loop or IOLoop.instance()

        self.initialize()
        self.user_data = None

        self.executor = ExecutorController(self.__io_loop, self.EXECUTABLE_PATH, self)
        self.user = UserClient(server_host, server_port, user_connection_id, docker_id,
                               self.__io_loop)
        self.user_connected = None

        if io_loop is None:
            IOLoop.instance().start()

    def initialize(self):
        pass

    @gen.coroutine
    def start(self):
        self.user_connected = yield self.user.connect()
        self.user.set_close_callback(self.on_close_user_connection)

        if not self.user_connected:
            logger.error("Bad connecting to main server")
            self.exit()
        try:
            yield self.on_ready()
        except Exception as e:
            logging.error(e, exc_info=True)
            self.user.send_error(e, traceback=sys.exc_info())
            self.exit()

    def on_close_user_connection(self):
        self.executor.kill_all()
        self.exit()

    @gen.coroutine
    def on_ready(self):
        self.user_data = yield self.user.send_select_data(data=['code', 'user_action'])
        user_action = self.user_data['user_action']
        yield {
            'run': self.run,
            'check': self.check,
            'run_in_console': self.run_in_console
        }[user_action]()

    def get_env_config(self, random_seed=None):
        env_config = {}
        if self.ENV_COVERCODE is not None and self.ENV_COVERCODE.get(self.CURRENT_ENV) is not None:
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
        self.exit()

    @gen.coroutine
    def run_in_console(self):
        logging.info("REFEREE:: run in console: {}".format(self.user_data['code']))
        exec_name = self.EXEC_NAME_RUN_IN_CONSOLE
        yield self.executor.start_env(exec_name=exec_name)
        yield self.executor.set_config(self.get_env_config(), exec_name=exec_name)
        yield self.executor.run_in_console(code=self.user_data['code'], exec_name=exec_name)

    @gen.coroutine
    def _continue_run_in_console(self):
        exec_name = self.EXEC_NAME_RUN_IN_CONSOLE
        data = yield self.user.send_select_data(data=['code'])
        logging.info("REFEREE:: continue console: {}".format(data))
        yield self.executor.run_in_console(code=data['code'], exec_name=exec_name)
        yield self._continue_run_in_console()


    @gen.coroutine
    def check(self):
        """
        Run code with different arguments from self.TESTS
        :return:
        """
        logging.info("CHECK:: Start checking")
        assert self.TESTS

        for category_name, tests in self.TESTS.items():
            try:
                yield self.check_category(category_name, tests)
            except exceptions.RefereeTestFailed as e:
                yield self.check_fail(points=e.points, additional_data=e.additional_data)
                return

        yield self.check_success()
        self.exit()

    @gen.coroutine
    def check_category(self, category_name, tests, **kwargs):
        logging.info("CHECK:: Start Category '{}' checking".format(category_name))
        yield self.executor.start_env(category_name)
        yield self.executor.set_config(self.get_env_config(), exec_name=category_name)

        code = self.user_data['code']
        result_code = yield self.executor.run_code(code=code, exec_name=category_name)

        if result_code.get("status") != "success":
            raise exceptions.RefereeTestFailed()

        for test_number, test in enumerate(tests):
            yield self.check_test_item(test, category_name=category_name, test_number=test_number)

        yield self.executor.kill(category_name)

    @gen.coroutine
    def check_test_item(self, test, category_name, test_number):
        yield self.pre_test(test)

        result_func = yield self.executor.run_func(
            function_name=self.FUNCTION_NAME or test["function_name"],
            args=test.get('input', None),
            exec_name=category_name)

        if result_func.get("status") != "success":
            description = "Category: {0}. Test {1} Run failed".format(category_name, test_number)
            raise exceptions.RefereeTestFailed(additional_data=description)
        validator = self.VALIDATOR(test)
        validator_result = validator.validate(result_func.get("result"))

        yield self.post_test(test, validator_result,
                             category_name=category_name, test_number=test_number)

        if not validator_result.test_passed:
            yield self.executor.kill(category_name)
            description = "Category: {0}. Test {1} Validate Failed".format(category_name,
                                                                           test_number)
            raise exceptions.RefereeTestFailed(additional_data=description)

    @gen.coroutine
    def pre_test(self, test, **kwargs):
        representation = self.CALLED_REPRESENTATIONS.get(self.CURRENT_ENV,
                                                         representations.base_representation)
        called_str = representation(test, self.FUNCTION_NAME)
        logging.info("PRE_TEST:: Called: {}".format(called_str))
        # TODO: Send data to Editor

    @gen.coroutine
    def post_test(self, test, validator_result, **kwargs):
        logging.info("POST_TEST:: Check result for category {0}, test {1}: {2}".format(
            kwargs.get("category_name", ""),
            kwargs.get("test_number", 0),
            validator_result.test_passed))
        if validator_result.additional_data:
            logging.info("VALIDATOR:: Data: {}".format(validator_result.additional_data))
            # TODO: Send data to Editor

    @gen.coroutine
    def check_result(self, success, points=None, additional_data=None):
        yield self.user.send_result(
            action=packet.RESULT_ACTION_CHECK,
            success=success,
            points=points,
            additional_data=additional_data
        )

    @gen.coroutine
    def check_success(self, points=None, additional_data=None):
        yield self.check_result(True, points, additional_data)

    @gen.coroutine
    def check_fail(self, points=None, additional_data=None):
        yield self.check_result(False, points, additional_data)

    def on_stdout(self, exec_name, line):
        logging.debug("STDOUT: " + line)
        IOLoop.current().spawn_callback(self.user.send_output_out, line)

    def on_stderr(self, exec_name, line):
        logging.debug("STDERR: " + line)
        IOLoop.current().spawn_callback(self.user.send_output_err, line)

    def exit(self):
        sys.exit()
