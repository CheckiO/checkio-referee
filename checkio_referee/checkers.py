"""
This library contains various predefined comparing and checking functions for referee class.
"""


def float_compare(first_float: float, second_float: float, precision: int=3) -> bool:
    """
    Compare two float numbers with the given accuracy

    :param first_float, second_float: Numbers to compare
    :param precision: Quantity of numbers after the dot to compare
    :return: Are they equal or not
    """
    return abs(first_float - second_float) <= 0.1 ** precision
