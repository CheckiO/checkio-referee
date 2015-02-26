"""
This library contains various predefined "covercodes" for referee.
"""

py_unwrap_args = """
def cover(func, data):
    return func(*data)
"""

py_2_str = """
def cover(func, data):
    return func(str(data))
"""

py_tuple = """
def cover(func, data):
    return func(tuple(data))
"""
