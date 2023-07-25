import yaml
import logging
from services.kubernetes_api import KubernetesAPI
from services.prometheus_api import PrometheusAPI
from services.metrics_fetcher import MetricsFetcher

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)
c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

# Load the configuration file
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    logger.info("Successfully loaded the config YAML file.")

# Setup APIs
k8s_api = KubernetesAPI()
prom_api = PrometheusAPI(config["prometheus"]["url"], config["prometheus"]["token"])

# Start fetching metrics
fetcher = MetricsFetcher(k8s_api, prom_api, config["prometheus"]["query_files"], logger)
fetcher.start()

# Keep the script running
while True:
    time.sleep(1)
