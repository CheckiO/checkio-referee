import logging
from tornado import gen

from checkio_referee import RefereeBase

DEFAULT_CATEGORY_POINTS = dict(("Rank_{:02d}".format(i), 100) for i in range(1, 10))


class RefereeRank(RefereeBase):
    CATEGORY_POINTS = DEFAULT_CATEGORY_POINTS

    @gen.coroutine
    def check(self):
        logging.info("CHECK:: Start checking")
        self.points = 0
        for category_name, tests in sorted(self.TESTS.items()):
            yield self.check_category(category_name, tests)
            self.points += self.CATEGORY_POINTS.get(category_name, 0)
        return (yield self.check_success(points=self.points))

    @gen.coroutine
    def check_fail(self, description=None, points=None):
        if self.points:
            return (yield self.check_success(description, self.points))
        else:
            return (yield self.user.post_check_fail(description))
