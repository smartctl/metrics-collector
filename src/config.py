# config.py
import yaml
import logging
import argparse
import os

class Config:
    def __init__(self):
        # Parse arguments first
        self.args = self.parse_args()

        # Set up the logger
        self.logger = self.setup_logger()

        # Load the configuration
        self.config_file = self.args.config if self.args.config else "config.yaml"
        self.config = self.load_config()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate", action="store_true", help="Only validate the Prometheus queries.")
        parser.add_argument("--config", help="Config file to use. (default config.yaml)")
        parser.add_argument("--collector_interval", type=int, help="Interval in seconds for metrics processing on a scheduler, not applicable with --validate")
        parser.add_argument("--output", choices=["parquet", "csv"], help="Format to save the metrics. Options: parquet, csv.")
        return parser.parse_args()

    def setup_logger(self):
        logger = logging.getLogger(__name__)
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(log_level)
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s (%(name)s) [%(levelname)s] %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
                self.logger.info("Successfully loaded the config YAML file.")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load the config YAML file due to {str(e)}")
            return None
