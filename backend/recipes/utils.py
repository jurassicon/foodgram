def get_short_string(input_string, length=40, suffix='...'):
    """
    Trims a given string to a specified maximum length and appends a suffix if
    it exceeds the length. If the input string's length is less than or equal
    to the specified length, it remains unchanged.
    """
    if len(input_string) <= length:
        return input_string
    return input_string[:length] + suffix
