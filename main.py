from src.metrics_processor import MetricsProcessor
from src.prometheus_api import PrometheusAPI
from src.config import Config
import sys

def main():
    # Initialize the Config class, which now handles logging, argument parsing, and loading config
    configuration = Config()
    if not configuration.config:
        sys.exit("Failed to load configuration. Exiting...")

    logger = configuration.logger
    config = configuration.config
    args = configuration.args

    # Extracting necessary configurations
    output_format = args.output or config.get("output", "parquet")
    
    # Handle query_mode
    query_mode = config.get("prometheus", {}).get("query_mode", "instant")
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

    # Extract collector_interval and possibly override
    collector_interval = config["collector"]["interval"]
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
