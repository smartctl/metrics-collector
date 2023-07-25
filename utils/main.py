import yaml
import logging
from services.kubernetes_api import KubernetesAPI
from services.prometheus_api import PrometheusAPI
from services.metrics_fetcher import MetricsFetcher
import time

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

# Get the scheduler interval, use_apps and namespaces from config file.
scheduler_interval = config.get('scheduler_interval', 100)
use_apps = config.get('use_apps', False)
namespaces = config.get('kubernetes', {}).get('namespaces', [])

# Start fetching metrics
fetcher = MetricsFetcher(k8s_api, prom_api, config["prometheus"]["query_sets"], logger, scheduler_interval, use_apps, namespaces)
fetcher.start()

# Keep the script running
while True:
    logger.info("Still running...")
    time.sleep(scheduler_interval)