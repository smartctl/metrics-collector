import csv
import requests
import yaml
import urllib3
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import time
from kubernetes import client, config

class KubernetesAPI:

    def __init__(self):
        config.load_kube_config()
        self.v1 = client.CoreV1Api()

    def get_app_names(self, namespace):
        ret = self.v1.list_namespaced_pod(namespace=namespace)
        return [i.metadata.name for i in ret.items]

    def get_all_namespaces(self):
        ret = self.v1.list_namespace()
        return [i.metadata.name for i in ret.items]


class PrometheusAPI:

    def __init__(self, url, token):
        self.url = url
        self.token = token
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.headers = {"Authorization": "Bearer " + token}

    def query(self, query):
        params = {
            "query": query,
            "time": round(time.time())
        }
        response = requests.get(
            self.url + "/api/v1/query",
            params=params,
            headers=self.headers,
            verify=False  # If the Prometheus instance uses self-signed SSL
        )
        response.raise_for_status()
        return response.json()["data"]["result"]


class MetricsFetcher:

    def __init__(self, k8s_api, prom_api, queries, logger, scheduler_interval=100):
        self.k8s_api = k8s_api
        self.prom_api = prom_api
        self.queries = queries
        self.logger = logger
        self.scheduler_interval = scheduler_interval
        self.scheduler = BackgroundScheduler()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.csv_file = f"metrics_{timestamp}.csv"
        
    def fetch_data(self, namespace):
        app_names = self.k8s_api.get_app_names(namespace)
        for app_name in app_names:
            self.logger.info(f"Fetching data for app: {app_name}, namespace: {namespace}.")
            data = {}
            for query in self.queries:
                formatted_query = query["query"].replace("{namespace}", namespace).replace("{app_name}", app_name)
                result = self.prom_api.query(formatted_query)
                if result:
                    value = result[0]["value"]
                    timestamp = value[0]
                    if timestamp not in data:
                        data[timestamp] = [app_name] + ['0.0']*len(self.queries)
                    data[timestamp][self.queries.index(query)+1] = value[1]
            self.write_to_csv(data)

    def write_to_csv(self, data):
        rows = [[timestamp] + values for timestamp, values in sorted(data.items())]
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["timestamp", "app_name"] + [q["metricName"] for q in queries])
            for row in rows:
                writer.writerow(row)
                self.logger.info(f"Appended data for timestamp {row[0]} to CSV file {self.csv_file}")

    def start(self):
        all_namespaces = self.k8s_api.get_all_namespaces()
        for namespace in all_namespaces:
            self.scheduler.add_job(self.fetch_data, 'interval', seconds=self.scheduler_interval, args=[namespace])
            self.logger.info(f"Scheduled the job to run every { self.scheduler_interval } seconds.")
            self.fetch_data(namespace)
        self.scheduler.start()


# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)
c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

# Load your YAML file
with open("queries1.yaml", "r") as f:
    queries = yaml.safe_load(f)
    logger.info("Successfully loaded the YAML file.")

# Setup APIs
k8s_api = KubernetesAPI()
prom_api = PrometheusAPI("https://prometheus-k8s-openshift-monitoring.apps.hubztp.telco.ocp.run",
                          "sha256~fiNsYzfBum-76aC6hS3auH_kNzG3xkYqrSsKXsiY3Lc")

# Start fetching metrics
fetcher = MetricsFetcher(k8s_api, prom_api, queries, logger)
fetcher.start()

# Keep the script running
while True:
    time.sleep(1)
