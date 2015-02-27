"""
This library contains various predefined comparing and checking classes for referee class.
"""


class ValidationError(Exception):
    pass


class BaseValidator(object):
    def __init__(self, test_data):
        self._test = test_data
        self.additional_data = None

    def validate(self, outer_result):
        raise NotImplementedError


class EqualValidator(BaseValidator):
    def validate(self, outer_result):
        if self._test.get("answer", None) != outer_result:
            raise ValidationError("Not equal")


class FloatEqualValidator(BaseValidator):
    PRECISION = 3

    def validate(self, outer_result):
        if abs(self._test.get("answer", 0) - outer_result) > 0.1 ** self.PRECISION:
            raise ValidationError("Out of the precision edges.")


class ExampleValidator(BaseValidator):
    def validate(self, outer_result):
        from random import randint

        self.additional_data = {"draw": [1, 1], "message": "Example message"}
        if randint(0, 1):
            raise ValidationError("Head. You Lose.")
