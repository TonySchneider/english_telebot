import os
import sys
import yaml
import logging
import platform
from pathlib import Path


class ConfigWrapper:
    os_system = platform.system()

    def __init__(self, load_folder: str = os.path.join('.', 'configurations')):
        """
        This class loads all our configurations yaml file and saves them as dictionary so we can use them quickly
        without open every time some configuration file.
        """
        self.load_folder = load_folder
        if not os.path.isdir(self.load_folder):
            self.load_folder = '.' + self.load_folder

        self.file_list = [
            f for f in Path(self.load_folder).iterdir() if f.is_file()
        ]
        self.all_data = self.parse_all_yaml_files()

    def parse_all_yaml_files(self) -> dict:
        """
        This method parses all the yaml files into a dict.
        :return: all files data as dict
        """
        all_files_data = {}

        for file in self.file_list:
            with open(file, 'r', encoding='utf8') as stream:
                try:
                    all_files_data[file.stem] = yaml.safe_load(stream)
                except yaml.YAMLError:
                    logging.exception(
                        f"There was an issue with {file} file. "
                        f"The system didn't manage to open it. "
                        f"\nAborting..."
                    )
                    sys.exit(1)

        return all_files_data

    def get_config_file(self, config_file_name: str) -> dict:
        """
        Returns data of the provided config file name.
        :param config_file_name: configurations yaml file name
        :return: dict
        """
        return self.all_data[config_file_name]
