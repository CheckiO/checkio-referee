import logging

from tornado import gen

from checkio_referee import RefereeBase


class RefereeCodeGolf(RefereeBase):
    DEFAULT_MAX_LINE_LENGTH = 1000
    MAX_LINE_LENGTH = {}  # key as language name
    BASE_POINTS = 0

    def count_code_length(self):
        return len(self.user_data['code'])

    @gen.coroutine
    def check_success(self, points=None, additional_data=None):
        code_length = self.count_code_length()
        max_length = self.MAX_LINE_LENGTH.get(self.CURRENT_ENV, self.DEFAULT_MAX_LINE_LENGTH)
        points = self.BASE_POINTS + max(max_length - code_length, 0)
        additional_data = {
            'description': "Code length: {}".format(code_length)
        }
        logging.info("SUCCESS:: Result: points {}, code length {}".format(points, code_length))
        yield super().check_success(points=points, additional_data=additional_data)
