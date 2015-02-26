"""
This library contains various predefined comparing and checking classes for referee class.
"""


class BaseVerification(object):
    def __init__(self, test_data, outer_result):
        self.test_data = test_data
        self.outer_result = outer_result
        self.additional_data = None
        self.test_passed = self.verify()

    def verify(self):
        raise NotImplementedError


class EqualVerification(BaseVerification):
    def verify(self):
        return self.test_data.get("answer", None) == self.outer_result


class FloatEqualVerification(BaseVerification):
    PRECISION = 3

    def verify(self):
        return abs(self.test_data.get("answer", 0) - self.outer_result) <= 0.1 ** self.PRECISION


class ExampleVerification(BaseVerification):
    def verify(self):
        self.additional_data = {"draw": [1, 1], "message": "Example message"}
        return False
