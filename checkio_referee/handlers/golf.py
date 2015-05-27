import logging

from tornado import gen

from checkio_referee.handlers.common import CheckHandler

logger = logging.getLogger(__name__)


class CodeGolfCheckHandler(CheckHandler):
    DEFAULT_MAX_CODE_LENGTH = 1000
    MAX_CODE_LENGTHS = {}  # key as environment name
    BASE_POINTS = 0
    COMMENT_MARKS = {
        "javascript": "//",
        "python_3": "#"
    }

    REFEREE_SETTINGS_PRIORITY = (CheckHandler.REFEREE_SETTINGS_PRIORITY +
                                 ('DEFAULT_MAX_CODE_LENGTH', 'MAX_CODE_LENGTHS',
                                  'BASE_POINTS', 'COMMENT_MARKS'))

    @property
    def code_length(self):
        lines = self.code.replace("\r\n", "\n").split("\n")
        result = 0
        comment_mark = self.COMMENT_MARKS.get(self.env_name)
        for line in lines:
            if comment_mark and line.lstrip().startswith(comment_mark):
                continue
            result += len(line) + 1
        return result - 1

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
