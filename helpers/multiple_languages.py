from wrappers.config_wrapper import ConfigWrapper


def load_dictionary(lang: str):
    return ConfigWrapper('lang').get_config_file(lang)
