"""
This library contains various predefined comparing and checking classes for referee class.
"""


class VerificationError(Exception):
    pass


class BaseVerification(object):
    def __init__(self, test_data):
        self._test = test_data
        self.additional_data = None

    def verify(self, outer_result):
        raise NotImplementedError


class EqualVerification(BaseVerification):
    def verify(self, outer_result):
        if self._test.get("answer", None) != outer_result:
            raise VerificationError("Not equal")


class FloatEqualVerification(BaseVerification):
    PRECISION = 3

    def verify(self, outer_result):
        if abs(self._test.get("answer", 0) - outer_result) > 0.1 ** self.PRECISION:
            raise VerificationError("Out of the precision edges.")


class ExampleVerification(BaseVerification):
    def verify(self, outer_result):
        from random import randint

        self.additional_data = {"draw": [1, 1], "message": "Example message"}
        if randint(0, 1):
            raise VerificationError("Head. You Lose.")
