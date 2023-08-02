import logging
import argparse
import os
from services.metrics_processor import MetricsProcessor
from services.prometheus_api import PrometheusAPI
from services.kubernetes_api import KubernetesAPI
from services.config import Config

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Only validate the Prometheus queries.")
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
    else:
        # Start the MetricsProcessor
        processor.start(nodes)

if __name__ == "__main__":
    main()
