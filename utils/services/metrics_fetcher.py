import csv
import time
import yaml
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

class MetricsFetcher:
    def __init__(self, k8s_api, prom_api, query_sets, logger, scheduler_interval=100, use_apps=False, namespaces=[]):
        self.k8s_api = k8s_api
        self.prom_api = prom_api
        self.logger = logger
        self.scheduler_interval = scheduler_interval
        self.use_apps = use_apps
        self.namespaces = namespaces
        self.scheduler = BackgroundScheduler()
        self.metrics_dir = "metrics_data"
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)
        self.query_sets = self.load_query_sets(query_sets)
        self.timestamp = time.strftime("%Y%m%d-%H%M%S")

    def load_query_sets(self, query_sets):
        loaded_query_sets = []
        for query_set in query_sets:
            x_features, y_labels = [], []
            for query_file in query_set["x_features"]:
                with open(query_file, "r") as f:
                    x_features.extend(yaml.safe_load(f))
            for query_file in query_set["y_labels"]:
                with open(query_file, "r") as f:
                    y_labels.extend(yaml.safe_load(f))
            loaded_query_sets.append({"name": query_set["name"], "x_features": x_features, "y_labels": y_labels})
        return loaded_query_sets

    def fetch_data(self, namespace):
        app_names = self.k8s_api.get_app_names(namespace) if self.use_apps else self.k8s_api.get_pod_names(namespace)

        for app_name in app_names:
            self.logger.info(f"Fetching data for app: {app_name}, namespace: {namespace}.")
            for query_set in self.query_sets:
                self.fetch_query_set_data(namespace, app_name, query_set)

    def fetch_query_set_data(self, namespace, app_name, query_set):
        csv_file = os.path.join(self.metrics_dir, f"{query_set['name']}_{self.timestamp}.csv")  # Use the instance's timestamp
        data = {}
        for query in query_set["x_features"] + query_set["y_labels"]:
            formatted_query = query["query"].replace("{namespace}", namespace).replace("{app_name}", app_name)
            try:
                result = self.prom_api.query(formatted_query)
                if result:
                    value = result[0]["value"]
                    timestamp = value[0]
                    data.setdefault(timestamp, [app_name] + ['0.0']*len(query_set["x_features"]) + ['0.0']*len(query_set["y_labels"]))
                    data[timestamp][query_set["x_features"].index(query)+1] = value[1]
            except Exception as e:
                self.logger.error(f"Failed to fetch data for query {formatted_query} due to {str(e)}")
                continue
        self.write_to_csv(data, csv_file, query_set)

    def write_to_csv(self, data, csv_file, query_set):
        rows = [[timestamp] + values for timestamp, values in sorted(data.items())]
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["timestamp", "app_name"] +
                                [q["metricName"] for q in query_set["x_features"]] +
                                [q["metricName"] for q in query_set["y_labels"]])
            for row in rows:
                try:
                    writer.writerow(row)
                    self.logger.info(f"Appended data for timestamp {row[0]} to CSV file {csv_file}")
                except Exception as e:
                    self.logger.error(f"Failed to write row {row} to CSV due to {str(e)}")
                    continue

    def start(self):
        all_namespaces = self.k8s_api.get_all_namespaces()
        if not self.namespaces:  # Empty dict, process all namespaces.
            namespaces_to_process = all_namespaces
        else:  # Process only those namespaces that exist and are in the config.
            namespaces_to_process = []
            for ns in self.namespaces:
                if ns in all_namespaces:
                    namespaces_to_process.append(ns)
                else:
                    self.logger.error(f"Namespace {ns} doesn't exist. Please check your configuration.")
                    
        for namespace in namespaces_to_process:
            self.scheduler.add_job(self.fetch_data, 'interval', seconds=self.scheduler_interval, args=[namespace])
            self.logger.info(f"Scheduled the job to run every { self.scheduler_interval } seconds.")
            self.fetch_data(namespace)
        self.scheduler.add_listener(self.my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.scheduler.start()

    def my_listener(self, event):
        if event.exception:
            self.logger.error('The job crashed :(')
        else:
            self.logger.info(f"Processing done. Waiting for the next round in { self.scheduler_interval } seconds...")
