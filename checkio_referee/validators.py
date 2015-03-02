"""
This library contains various predefined comparing and checking classes for referee class.
"""
from random import randint


class ValidatorResult(object):
    def __init__(self, test_passed, additional_data=None):
        self.test_passed = test_passed
        self.additional_data = additional_data


class BaseValidator(object):
    def __init__(self, test_data):
        self._test = test_data
        self.additional_data = None

    def validate(self, outer_result):
        raise NotImplementedError


class EqualValidator(BaseValidator):
    def validate(self, outer_result):
        if self._test.get("answer", None) != outer_result:
            return ValidatorResult(False)
        return ValidatorResult(True)


class FloatEqualValidator(BaseValidator):
    PRECISION = 3

    def validate(self, outer_result):
        if abs(self._test.get("answer", 0) - outer_result) > 0.1 ** self.PRECISION:
            return ValidatorResult(False)
        return ValidatorResult(True)


class ExampleValidator(BaseValidator):
    def validate(self, outer_result):
        additional_data = {"draw": [1, 1], "message": "Example message"}
        if randint(0, 1):
            return ValidatorResult(False, additional_data)
        return ValidatorResult(True, additional_data)
