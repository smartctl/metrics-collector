# config.py
import yaml
import logging
import argparse
import os
import sys
from src.stats import FileStats

class Config:
    def __init__(self):
        # Parse arguments first
        self.args = self.parse_args()

        # Set up the logger
        self.logger = self.setup_logger()

        # Load the configuration
        self.config_file = self.args.config if self.args.config else "config.yaml"
        self.config = self.load_config()

        # Validate and set default configurations
        self.validate_configs()
        
        # Override configurations using CLI arguments
        self.override_with_arguments()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate", action="store_true", help="Only validate the Prometheus queries.")
        parser.add_argument("--config", help="Config file to use. (default config.yaml)")
        parser.add_argument("--collector_interval", type=int, help="Interval in seconds for metrics processing on a scheduler, not applicable with --validate")
        parser.add_argument("--output_path", help="Override the path to write files from configuration.")
        parser.add_argument("--output_format", choices=["csv", "parquet"], help="Override the file format from configuration. Options: parquet, csv.")
        parser.add_argument("--compression", choices=["", "GZIP", "snappy", "brotli"], 
                            help="Override the compression format from configuration. Options: 'GZIP', 'snappy', 'brotli'. Leave empty for no compression.")
        parser.add_argument("--stats", action="store_true", help="Display statistics about a data file.")
        parser.add_argument("--filename", type=str, help="Full path of the file for which to display statistics. Required if --stats is provided.")
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

    def validate_configs(self):
        # Handle destination configurations
        self.destination_path = self.config.get("destination", {}).get("path", "data/collection")
        self.file_format = self.config.get("destination", {}).get("file_format", "parquet")
        self.compression = self.config.get("destination", {}).get("compression", "")

        # Validations for query_mode and time_range
        self.query_mode = self.config.get("prometheus", {}).get("query_mode", "instant")
        self.time_range = self.config.get("prometheus", {}).get("time_range") if self.query_mode == "range" else None

        # Setting default collector_interval
        self.collector_interval = self.config["collector"]["interval"]

    def override_with_arguments(self):
        # Override destination configurations with command-line arguments, if provided
        if self.args.output_path:
            self.destination_path = self.args.output_path
        if self.args.output_format:
            self.file_format = self.args.output_format
        if self.args.compression:
            self.compression = self.args.compression

        # Override other configurations using command-line arguments
        if self.args.output_format:
            self.output_format = self.args.output_format
        if self.args.collector_interval:
            self.collector_interval = self.args.collector_interval
        
        # Post-override validations
        if self.file_format not in ["csv", "parquet"]:
            self.logger.error("Invalid file_format specified. Only 'csv' and 'parquet' are supported.")
            sys.exit(1)
        
        if self.compression and self.compression not in ["", "GZIP", "snappy", "brotli"]:
            self.logger.error("Invalid compression format. Supported options are 'GZIP', 'snappy', 'brotli' or leave empty for no compression.")
            sys.exit(1)

    def is_stats_mode(self):
        return self.args.stats

    def get_filename_for_stats(self):
        if not self.args.filename:
            self.logger.error("Please provide a valid filename with the --filename option.")
            sys.exit(1)
        return self.args.filename

    def get_stats(self):
        try:
            stats_obj = FileStats(self.get_filename_for_stats())
            stats_obj.print_summary()
        except FileNotFoundError:
            self.logger.error(f"The file '{self.get_filename_for_stats()}' does not exist. Please provide a valid file path.")
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}")
