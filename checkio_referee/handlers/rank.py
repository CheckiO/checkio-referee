import logging

from tornado import gen

from checkio_referee import exceptions
from checkio_referee.handlers.common import CheckHandler

logger = logging.getLogger(__name__)
DEFAULT_CATEGORY_POINTS = dict(("Rank_{:02d}".format(i), 100) for i in range(1, 10))


class RankCheckHandler(CheckHandler):
    CATEGORY_POINTS = DEFAULT_CATEGORY_POINTS

    REFEREE_SETTINGS_PRIORITY = CheckHandler.REFEREE_SETTINGS_PRIORITY + ('CATEGORY_POINTS',)

    @gen.coroutine
    def start(self):
        logger.info("RankCheckHandler:: Start checking")
        assert self.TESTS

        points = 0
        for category_name, tests in sorted(self.TESTS.items()):
            try:
                yield self.check_category(self.code, category_name, tests)
            except exceptions.RefereeExecuteFailed as e:
                if points:
                    yield self.result_check_success(points=points)
                else:
                    yield self.result_check_fail(additional_data=e.additional_data)
                return
            points += self.CATEGORY_POINTS.get(category_name, 0)

        yield self.result_check_success(points=points)
        self.stop()
