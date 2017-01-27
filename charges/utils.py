def int_if_close(floating_number, tolerance=0.001):
    if abs(round(floating_number, 0) - floating_number) <= tolerance:
        return round(floating_number, 0)
    return floating_number
