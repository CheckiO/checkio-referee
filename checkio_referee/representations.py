"""
This library contains various predefined called code representations for referee.
"""


def base_representation(test, function_name):
    return "{}({})".format(function_name, test["input"])


def unwrap_arg_representation(test, function_name):
    return "{}({})".format(function_name, ", ".join(str(d) for d in test["input"]))


def py_tuple_representation(test, function_name):
    return "{}({})".format(function_name, tuple(test["input"]))
