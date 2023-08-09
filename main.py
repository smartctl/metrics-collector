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
    parser.add_argument("--output", choices=["parquet", "csv"], help="Format to save the metrics. Options: parquet, csv.")
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

    output_format = "parquet"
    if args.output:
        output_format = args.output
    elif "output" in config:
        output_format = config["output"]

    # Handle query_mode
    query_mode = config.get("prometheus", {}).get("query_mode", "instant")  # defaulting to "instant"
    if query_mode not in ["instant", "range"]:
        logger.error(f"Invalid query_mode '{query_mode}' specified. Allowed values are 'instant' and 'range'. Exiting...")
        sys.exit(1)

    # Handle time_range
    time_range = None
    if query_mode == "range":
        time_range = config.get("prometheus", {}).get("time_range")
        if not time_range:
            logger.error("time_range is required when query_mode is 'range'. Exiting...")
            sys.exit(1)

    # Read the collector_interval from config.yaml
    collector_interval = config["collector"]["interval"]
    # Override the collector_interval if provided through the command-line argument
    if args.collector_interval:
        collector_interval = args.collector_interval

    # Create the Prometheus API client
    prom_api = PrometheusAPI(config["prometheus"]["url"], config["prometheus"]["token"], logger)

    # Create the MetricsProcessor
    processor = MetricsProcessor(prom_api, config["prometheus"]["query_sets"], query_mode, time_range, logger, output_format=output_format)

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
