from checkio_referee import RefereeBase
import logging


class RefereeCodeGolf(RefereeBase):
    DEFAULT_LENGTH = 1000
    FOR_LANGUAGE_LENGTHS = {
        "some_language_with_specific_length": 1001
    }
    BASE_POINTS = 0

    def count_code_length(self):
        return len(self.user_data['code'])

    def check_success(self, description=None, points=None):
        code_length = self.count_code_length()
        max_length = self.FOR_LANGUAGE_LENGTHS.get(self.CURRENT_ENV, self.DEFAULT_LENGTH)
        result_points = self.BASE_POINTS + max(max_length - code_length, 0)
        logging.info("SUCCESS:: Result: points {}, code length {}".format(
            result_points, code_length))
        return (yield self.user.post_check_success(
            description="Code length: {}".format(code_length), points=result_points))
