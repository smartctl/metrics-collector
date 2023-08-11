# main.py
from src.metrics_processor import MetricsProcessor
from src.prometheus_api import PrometheusAPI
from src.config import Config
import sys

def main():
    # Initialize the Config class
    configuration = Config()
    if not configuration.config:
        sys.exit("Failed to load configuration. Exiting...")

    logger = configuration.logger

    # Create the Prometheus API client
    prom_api = PrometheusAPI(configuration.config["prometheus"]["url"], configuration.config["prometheus"]["token"], logger)

    # Create the MetricsProcessor
    processor = MetricsProcessor(prom_api,
                                 configuration.config["prometheus"]["query_sets"], 
                                 configuration.query_mode,
                                 configuration.time_range,
                                 logger,
                                 file_format=configuration.file_format,
                                 destination_path=configuration.destination_path,
                                 compression=configuration.compression)

    if configuration.args.validate:
        # Only validate the Prometheus queries
        processor.validate_queries()
    else:
        # Run metrics processing on a scheduler
        # if collector_interval = 0 then run metrics processing only once
        try:
            processor.start(configuration.collector_interval)
        except KeyboardInterrupt:
            logger.info(f"CTRL + C (SIGINT) detected. Shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()
