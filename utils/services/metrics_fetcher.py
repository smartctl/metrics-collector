import csv
from apscheduler.schedulers.background import BackgroundScheduler
import time
import yaml
import os

class MetricsFetcher:
    def __init__(self, k8s_api, prom_api, query_files, logger, scheduler_interval=100, use_apps=False, namespaces=[]):
        self.k8s_api = k8s_api
        self.prom_api = prom_api
        self.promql_queries = []
        for query_file in query_files:
            with open(query_file, "r") as f:
                self.promql_queries.extend(yaml.safe_load(f))
        self.logger = logger
        self.scheduler_interval = scheduler_interval
        self.use_apps = use_apps
        self.namespaces = namespaces
        self.scheduler = BackgroundScheduler()
        self.metrics_dir = "metrics_data"
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.csv_file = os.path.join(self.metrics_dir, f"metrics_{timestamp}.csv")

    def fetch_data(self, namespace):
        if self.use_apps:
            app_names = self.k8s_api.get_app_names(namespace)
        else:
            app_names = self.k8s_api.get_pod_names(namespace)

        for app_name in app_names:
            self.logger.info(f"Fetching data for app: {app_name}, namespace: {namespace}.")
            data = {}
            for query in self.promql_queries:
                formatted_query = query["query"].replace("{namespace}", namespace).replace("{app_name}", app_name)
                result = self.prom_api.query(formatted_query)
                if result:
                    value = result[0]["value"]
                    timestamp = value[0]
                    if timestamp not in data:
                        data[timestamp] = [app_name] + ['0.0']*len(self.promql_queries)
                    data[timestamp][self.promql_queries.index(query)+1] = value[1]
            self.write_to_csv(data)

    def write_to_csv(self, data):
        rows = [[timestamp] + values for timestamp, values in sorted(data.items())]
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["timestamp", "app_name"] + [q["metricName"] for q in self.promql_queries])
            for row in rows:
                writer.writerow(row)
                self.logger.info(f"Appended data for timestamp {row[0]} to CSV file {self.csv_file}")

    def start(self):
        if not self.namespaces:  # Empty list, process all namespaces.
            namespaces_to_process = self.k8s_api.get_all_namespaces()
        else:  # Process only those namespaces that exist and are in the config.
            namespaces_to_process = []
            all_namespaces = self.k8s_api.get_all_namespaces()
            for ns in self.namespaces:
                if ns in all_namespaces:
                    namespaces_to_process.append(ns)
                else:
                    self.logger.error(f"Namespace {ns} doesn't exist. Please check your configuration.")
                    
        for namespace in namespaces_to_process:
            self.scheduler.add_job(self.fetch_data, 'interval', seconds=self.scheduler_interval, args=[namespace])
            self.logger.info(f"Scheduled the job to run every { self.scheduler_interval } seconds.")
            self.fetch_data(namespace)
        self.scheduler.start()

