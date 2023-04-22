import string

from wrappers.config_wrapper import ConfigWrapper


def load_dictionary(lang: str):
    return ConfigWrapper('lang').get_config_file(lang)


def is_english(text):
    """
    Returns True if the input text contains only English characters, False otherwise.
    """
    for char in text:
        if char not in string.printable or not char.isascii():
            return False
    return True
