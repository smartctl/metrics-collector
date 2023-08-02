import logging
import argparse
import os
import time
from services.metrics_processor import MetricsProcessor
from services.prometheus_api import PrometheusAPI
from services.kubernetes_api import KubernetesAPI
from services.config import Config


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Only validate the Prometheus queries.")
    parser.add_argument("--scheduler_interval", type=int, help="Interval in seconds for metrics processing on a scheduler, not applicable with --validate")
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
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(ch)

    # Load the config
    config = Config("config.yaml", logger).config

    # Read the scheduler_interval from config.yaml
    scheduler_interval = config.get("scheduler_interval")
    # Override the scheduler_interval if provided through the command-line argument
    if args.scheduler_interval:
        scheduler_interval = args.scheduler_interval

    # Create the Prometheus API client
    prom_api = PrometheusAPI(config["prometheus"]["url"], config["prometheus"]["token"], logger)

    # Create the Kubernetes API client
    k8s_api = KubernetesAPI(logger)

    # Get the number of nodes
    node_count = k8s_api.get_node_count()
    nodes = [f"node{i+1}" for i in range(node_count)]

    # Create the MetricsProcessor
    processor = MetricsProcessor(prom_api, config["prometheus"]["query_sets"], logger)


    if args.validate:
        # Only validate the Prometheus queries
        processor.validate_queries(nodes)
    elif scheduler_interval:
        # Run metrics processing on a scheduler
        processor.start(nodes, scheduler_interval)
    else:
        # Run metrics processing only once
        processor.start(nodes)

if __name__ == "__main__":
    main()
