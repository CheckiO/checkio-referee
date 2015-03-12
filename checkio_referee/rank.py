import logging

from tornado import gen

from checkio_referee import RefereeBase, exceptions


DEFAULT_CATEGORY_POINTS = dict(("Rank_{:02d}".format(i), 100) for i in range(1, 10))


class RefereeRank(RefereeBase):
    CATEGORY_POINTS = DEFAULT_CATEGORY_POINTS

    @gen.coroutine
    def check(self):
        logging.info("CHECK:: Start checking")
        points = 0
        for category_name, tests in sorted(self.TESTS.items()):
            try:
                yield self.check_category(category_name, tests)
            except exceptions.RefereeTestFailed as e:
                if points:
                    yield self.result_check_success(points=points)
                else:
                    yield self.result_check_fail(additional_data=e.additional_data)
                return
            points += self.CATEGORY_POINTS.get(category_name, 0)

        yield self.result_check_success(points=points)
        self.exit()
