# config.py
import yaml
import logging

class Config:
    def __init__(self, config_file, logger):
        self.config_file = config_file
        self.logger = logger
        self.config = self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
                self.logger.info("Successfully loaded the config YAML file.")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load the config YAML file due to {str(e)}")
            return None
