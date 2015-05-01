"""
This library contains various predefined comparing and checking classes for referee class.
"""
from random import choice


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
        return ValidatorResult(self._test.get("answer", None) == outer_result)


class FloatEqualValidator(BaseValidator):
    PRECISION = 3

    def validate(self, outer_result):
        if not isinstance(outer_result, (int, float)):
            return ValidatorResult(False, "The result should be a float or integer.")
        diff = abs(self._test.get("answer", 0) - outer_result)
        return ValidatorResult(diff <= 0.1 ** self.PRECISION, diff)


class ExampleValidator(BaseValidator):
    def validate(self, outer_result):
        return ValidatorResult(choice((True, False)),
                               {"draw": [1, 1], "message": "Example message", "number": 42})
