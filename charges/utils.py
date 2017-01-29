import periodictable


def int_if_close(floating_number, tolerance=0.001):
    if abs(round(floating_number, 0) - floating_number) <= tolerance:
        return round(floating_number, 0)
    return floating_number


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
