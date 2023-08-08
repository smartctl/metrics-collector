import logging
import argparse
import os
import sys
from src.metrics_processor import MetricsProcessor
from src.prometheus_api import PrometheusAPI
from src.config import Config


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Only validate the Prometheus queries.")
    parser.add_argument("--config", help="Config file to use. (default config.yaml)")
    parser.add_argument("--collector_interval", type=int, help="Interval in seconds for metrics processing on a scheduler, not applicable with --validate")
    args = parser.parse_args()

    # Create a logger
    logger = logging.getLogger(__name__)

    # Set the log level based on the LOG_LEVEL environment variable
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s (%(name)s) [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(ch)

    # Load the general config
    if args.config:
        config = Config(args.config, logger).config
    else:
        config = Config("config.yaml", logger).config

    # Read the collector_interval from config.yaml
    collector_interval = config["collector"]["interval"]
    # Override the collector_interval if provided through the command-line argument
    if args.collector_interval:
        collector_interval = args.collector_interval

    # Create the Prometheus API client
    prom_api = PrometheusAPI(config["prometheus"]["url"], config["prometheus"]["token"], logger)

    # Create the MetricsProcessor
    processor = MetricsProcessor(prom_api, config["prometheus"]["query_sets"], logger)

    if args.validate:
        # Only validate the Prometheus queries
        processor.validate_queries()
    else:
        # Run metrics processing on a scheduler
        # if collector_interval = 0 then run metrics processing only once
        try:
            processor.start(collector_interval)
        except KeyboardInterrupt:
            logger.info(f"CTRL + C (SIGINT) detected. Shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()
