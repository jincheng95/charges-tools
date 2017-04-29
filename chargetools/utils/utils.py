import re
from io import BytesIO

import numpy as np
import periodictable


def int_if_close(floating_number, tolerance=0.0001):
    """
    Numbers printed in log files etc. (even integers) may have many decimal places.
        In programming integers may be more useful.
        This function converts such floating numbers to integers.

    :type floating_number: float | str
    :param floating_number: Floating number which may be better represented an integer.
    :type tolerance: float
    :param tolerance: If the number is within this range of its closest integer, then output an integer object.
    :rtype: int | float
    :return: Integer or float, depending on whether the input is close enough to its closest integer.
    """
    floating_number = float(floating_number)
    if abs(round(floating_number, 0) - floating_number) <= tolerance:
        return round(floating_number, 0)
    return floating_number


def chained_or(*args):
    if args:
        res = args[0]
        for arg in args[1:]:
            res = np.logical_or(res, arg)
        return res
    return False


def atomic_number_to_symbol(number):
    for element in periodictable.elements:
        if element.number == number:
            return element.symbol
    return None


def symbol_to_atomic_number(symbol):
    for element in periodictable.elements:
        if element.symbol == symbol:
            return element.number
    return None


def skip_til_occurence(iterator, line_re, count_until):
    count = 0
    while count < count_until:
        line = next(iterator)
        if re.search(line_re, line):
            count += 1


def consume_lines(iterator, skip=3, include_regex=r'\S'):
    res = ""
    count = 0

    line = next(iterator)
    while re.search(include_regex, line):
        if count >= skip:
            res += line

        count += 1
        line = next(iterator)
    return res


def genfromstring(string, *args, **kwargs):
    s = BytesIO(string.encode())
    return np.genfromtxt(s, *args, **kwargs)