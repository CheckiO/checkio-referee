import logging

from tornado import gen
from tornado.ioloop import IOLoop

from checkio_referee import exceptions
from checkio_referee.handlers.base import BaseHandler
from checkio_referee.utils import validators
from checkio_referee.utils.representations import base_representation

logger = logging.getLogger(__name__)


class RunHandler(BaseHandler):

    @gen.coroutine
    def start(self):
        self.environment = yield self.get_environment(self.env_name)
        try:
            if 'pleasekillme' in self.code:
                raise ValueError('PleaseKillMe')
            yield self.environment.run_code(code=self.code)
        except exceptions.EnvironmentRunFail:
            pass
        yield self.environment.stop()
        yield self.editor_client.send_run_finish(code=self.code)
        self.stop()


class RunInConsoleHandler(BaseHandler):

    @gen.coroutine
    def start(self):
        self.environment = yield self.get_environment(self.env_name)
        try:
            yield self.environment.run_in_console(code=self.code)
        except exceptions.EnvironmentRunFail:
            pass
        else:
            yield self._continue_run_in_console()

    @gen.coroutine
    def _continue_run_in_console(self):
        editor_data = yield self.editor_client.send_select_data(data=['code'])
        try:
            yield self.environment.run_in_console(code=editor_data['code'])
        except exceptions.EnvironmentRunFail:
            pass
        else:
            yield self._continue_run_in_console()


class CheckHandler(BaseHandler):
    TESTS = None

    DEFAULT_FUNCTION_NAME = 'checkio'
    FUNCTION_NAMES = {}

    ENV_COVERCODE = None
    VALIDATOR = validators.EqualValidator

    CALLED_REPRESENTATIONS = {}

    REFEREE_SETTINGS_PRIORITY = (
        'TESTS',
        'DEFAULT_FUNCTION_NAME',
        'FUNCTION_NAMES',
        'ENV_COVERCODE',
        'VALIDATOR',
        'CALLED_REPRESENTATIONS',
    )

    @property
    def function_name(self):
        return self.FUNCTION_NAMES.get(self.env_name, self.DEFAULT_FUNCTION_NAME)

    @gen.coroutine
    def start(self):
        print('START')
        logger.debug("CheckHandler:: Start checking")
        assert self.TESTS

        for category_name, tests in sorted(self.TESTS.items()):
            try:
                yield self.check_category(self.code, category_name, tests)
            except exceptions.RefereeExecuteFailed as e:
                yield self.result_check_fail(points=e.points, additional_data=e.additional_data)
                return
            except Exception:
                yield self.result_check_fail()
                raise

        yield self.result_check_success()
        self.stop()

    @gen.coroutine
    def check_category(self, code, category_name, tests, **kwargs):
        logger.debug("CHECK:: Start Category '{}' checking".format(category_name))

        environment = self.environment = yield self.get_environment(self.env_name)
        yield environment.set_config(self.get_env_config())

        try:
            yield environment.run_code(code=code)
        except exceptions.EnvironmentRunFail:
            raise exceptions.RefereeCodeRunFailed()

        for test_number, test in enumerate(tests):
            test_passed = yield self.check_test_item(environment, test, category_name, test_number)
            if not test_passed:
                yield environment.stop()
                description = "Category: {0}. Test {1} Validate Failed".format(category_name,
                                                                               test_number)
                raise exceptions.RefereeTestFailed(description=description)

        yield environment.stop()

    @gen.coroutine
    def check_test_item(self, environment, test, category_name, test_number):
        io_loop = IOLoop.current()
        io_loop.spawn_callback(self.pre_test, test=test)

        function_name = test.get("function_name") or self.function_name
        params = test.get('input', None)
        try:
            result_func = yield environment.run_func(function_name=function_name, params=params)
        except exceptions.EnvironmentRunFail:
            description = "Category: {0}. Test {1} Run failed".format(category_name, test_number)
            raise exceptions.RefereeTestFailed(description=description)

        run_result = result_func.get("result")
        validator = self.VALIDATOR(test)
        validator_result = validator.validate(run_result)

        io_loop.spawn_callback(self.post_test, test=test, validator_result=validator_result,
                               category_name=category_name, test_number=test_number,
                               run_result=run_result)

        return validator_result.test_passed

    @gen.coroutine
    def pre_test(self, test):
        representation = self.CALLED_REPRESENTATIONS.get(self.env_name, base_representation)
        called_str = representation(test, self.function_name)
        logger.debug("PRE_TEST:: Called: {}".format(called_str))
        yield self.editor_client.send_pre_test({
            'representation': called_str
        })

    @gen.coroutine
    def post_test(self, test, validator_result, category_name, test_number, run_result):
        logger.debug("POST_TEST:: Check result for category {0}, test {1}: {2}\n"
                     "VALIDATOR: {3}".format(
            category_name,
            test_number,
            validator_result.test_passed,
            validator_result.additional_data
        ))
        yield self.editor_client.send_post_test({
            'actual_result': run_result,
            'expected_result': test.get('answer'),
            'test_passed': validator_result.test_passed,
            'additional_data': validator_result.additional_data
        })

    def get_env_config(self, random_seed=None):
        env_config = {
            'is_checking': True
        }
        if self.ENV_COVERCODE is not None and self.ENV_COVERCODE.get(self.env_name) is not None:
            env_config['cover_code'] = self.ENV_COVERCODE[self.env_name]
        if random_seed is not None:
            env_config['random_seed'] = random_seed
        return env_config

    @gen.coroutine
    def _result_check(self, success, points=None, additional_data=None):
        print('RESULT SEND')
        yield self.editor_client.send_check_result(
            success=success,
            code=self.code,
            points=points,
            additional_data=additional_data
        )

    @gen.coroutine
    def result_check_success(self, points=None, additional_data=None):
        yield self._result_check(True, points, additional_data)

    @gen.coroutine
    def result_check_fail(self, points=None, additional_data=None):
        yield self._result_check(False, points, additional_data)
