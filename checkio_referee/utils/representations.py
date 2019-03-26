"""
This library contains various predefined called code representations for referee.
"""

__all__ = ["base_representation", "unwrap_arg_representation",
           "py_tuple_representation", "input_representation"]


def ext_str(data) -> str:
    """
    Extended str data conversion with quotes for strings.

    :param data: data for conversion
    :return: string representation
    """
    return '"{}"'.format(data) if isinstance(data, str) else str(data)


def base_representation(test, function_name):
    return "{}({})".format(function_name, ext_str(test["input"]))

def input_representation(test):
    return ext_str(test["input"])

def unwrap_arg_representation(test, function_name):
    arguments = ", ".join(ext_str(d) for d in test["input"])
    return "{}({})".format(function_name, arguments)


def py_tuple_representation(test, function_name):
    return "{}({})".format(function_name, tuple(test["input"]))
