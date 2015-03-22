import logging

from tornado import gen

from checkio_referee.handlers.common import CheckHandler

logger = logging.getLogger(__name__)


class CodeGolfCheckHandler(CheckHandler):
    DEFAULT_MAX_CODE_LENGTH = 1000
    MAX_CODE_LENGTHS = {}  # key as environment name
    BASE_POINTS = 0

    @property
    def code_length(self):
        return len(self.code)

    @gen.coroutine
    def result_check_success(self, points=None, additional_data=None):
        code_length = self.code_length
        max_length = self.MAX_CODE_LENGTHS.get(self.env_name, self.DEFAULT_MAX_CODE_LENGTH)
        points = self.BASE_POINTS + max(max_length - code_length, 0)
        additional_data = {
            'description': "Code length: {}".format(code_length)
        }
        logger.debug("CheckHandler:: success points {} code length {}".format(points, code_length))
        yield super().result_check_success(points=points, additional_data=additional_data)
