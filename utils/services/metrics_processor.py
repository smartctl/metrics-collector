import csv
import os
import yaml
import time

class MetricsProcessor:
    def __init__(self, prom_api, query_sets, logger, metrics_dir="processed_metrics_data"):
        self.prom_api = prom_api
        self.logger = logger
        self.metrics_dir = metrics_dir
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)
        self.query_sets = self.load_query_sets(query_sets)
        self.csv_data = {}
        self.timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.logger.debug("MetricsProcessor initialized.")

    def load_query_sets(self, query_sets):
        loaded_query_sets = {"features": [], "labels": []}
        for query_set in query_sets:
            if "features" in query_set:  # Changed from query_sets to query_set
                for query_file in query_set["features"]:
                    with open(query_file, "r") as f:
                        loaded_query_sets["features"].extend(yaml.safe_load(f))
            if "labels" in query_set:  # Changed from query_sets to query_set
                for query_file in query_set["labels"]:
                    with open(query_file, "r") as f:
                        loaded_query_sets["labels"].extend(yaml.safe_load(f))
        self.logger.debug(f"Loaded query sets: {loaded_query_sets}")
        return loaded_query_sets


    def fetch_metrics(self, metric):
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"]
                self.logger.debug(f"Fetched data for {metric['name']}: {value}")
                return value[1]
        except Exception as e:
            self.logger.error(f"Failed to fetch data for metric {metric['name']} due to {str(e)}")
            return None

    def process_metrics(self, nodes, skill_name):
        for metric in self.query_sets[skill_name]:
            self.logger.debug(f"Processing metric: {metric['name']}, type: {metric['type']}")
            if metric["type"] == "scalar":
                self.process_scalar_metrics(metric)
            elif metric["type"].endswith("per_node"):
                self.process_per_node_metrics(metric, nodes)
            elif metric["type"].endswith("per_node_per_attribute"):
                self.process_per_node_per_attribute_metrics(metric, nodes)
            elif metric["type"] == "boolean":
                self.process_boolean_metrics(metric)
            elif metric["type"] == "scalar_per_attribute":
                self.process_scalar_per_attribute_metrics(metric)

    def process_per_node_per_attribute_metrics(self, metric, nodes):
        self.logger.debug(f"Processing per_node_per_attribute metrics for {metric['name']}.")
        for node in nodes:
            try:
                formatted_query = metric["expr"].replace("{node}", node)
                result = self.prom_api.query(formatted_query)
                for item in result:
                    # Prepare list to gather all attribute values
                    attribute_values = []
                    for attribute, value in item['metric'].items():
                        # Exclude 'node' attribute because we already consider node in csv_data key
                        if attribute != 'node':
                            attribute_values.append(value)
                    
                    # Join all attribute values with underscore to create final attribute name
                    attribute = '_'.join(attribute_values) if attribute_values else 'default'
                    
                    value = item['value'][1]
                    self.csv_data[f"{node}_{metric['name']}_{attribute}"] = value
            except Exception as e:
                self.logger.error(f"Failed to fetch data for query {formatted_query} due to {str(e)}")

    def process_scalar_metrics(self, metric):
        self.logger.debug(f"Processing scalar metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"][1]
                self.csv_data[metric["name"]] = value
        except Exception as e:
            self.logger.error(f"Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_per_node_metrics(self, metric, nodes):
        self.logger.debug(f"Processing per_node metrics for {metric['name']}.")
        for node in nodes:
            try:
                formatted_query = metric["expr"].replace("{node}", node)
                result = self.prom_api.query(formatted_query)
                if result:
                    value = result[0]["value"][1]
                    self.csv_data[f"{node}_{metric['name']}"] = value
            except Exception as e:
                self.logger.error(f"Failed to fetch data for query {formatted_query} due to {str(e)}")

    def process_boolean_per_node_metrics(self, metric, nodes):
        self.logger.debug(f"Processing boolean_per_node metrics for {metric['name']}.")
        for node in nodes:
            try:
                formatted_query = metric["expr"].replace("{node}", node)
                result = self.prom_api.query(formatted_query)
                if result:
                    value = result[0]["value"][1]
                    self.csv_data[f"{node}_{metric['name']}"] = 'green' if value == '0' else metric['label']
            except Exception as e:
                self.logger.error(f"Failed to fetch data for query {formatted_query} due to {str(e)}")

    def process_boolean_metrics(self, metric):
        self.logger.debug(f"Processing boolean metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"][1]
                self.csv_data[metric["name"]] = value
        except Exception as e:
            self.logger.error(f"Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_scalar_per_attribute_metrics(self, metric):
        self.logger.debug(f"Processing scalar_per_attribute metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                for res in result:
                    # Prepare list to gather all attribute values
                    attribute_values = []
                    for attribute, value in res['metric'].items():
                        attribute_values.append(value)
                    
                    # Join all attribute values with underscore to create final attribute name
                    attribute = '_'.join(attribute_values) if attribute_values else 'default'
                    
                    value = res["value"][1]
                    self.csv_data[f"{metric['name']}_{attribute}"] = value
        except Exception as e:
            self.logger.error(f"Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def save_to_csv(self, skill_name):
        self.logger.debug(f"Saving data to CSV file for {skill_name}.")
        # Create the directory if it doesn't exist
        if not os.path.exists('metrics_data'):
            os.makedirs('metrics_data')

        # Create the filename
        filename = f'metrics_data/metrics_{skill_name}_{self.timestamp}.csv'

        # Check if the file already exists
        file_exists = os.path.exists(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = self.csv_data.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # If the file doesn't exist, write the header
            if not file_exists:
                writer.writeheader()

            # Write the row of data
            if self.csv_data:  # Only write a row of data if there is any
                writer.writerow(self.csv_data)

        self.logger.debug(f"Appended data to CSV file {filename}")

    def validate_queries(self, nodes):
        for skill_name in ["features", "labels"]:
            for metric in self.query_sets[skill_name]:
                try:
                    if metric["type"] == "scalar":
                        self.fetch_metrics(metric)
                    elif metric["type"].endswith("per_node"):
                        for node in nodes:
                            metric["expr"] = metric["expr"].replace("{node}", node)
                            self.fetch_metrics(metric)
                    elif metric["type"].endswith("per_node_per_attribute"):
                        for node in nodes:
                            metric["expr"] = metric["expr"].replace("{node}", node)
                            self.fetch_metrics(metric)
                    elif metric["type"] == "boolean":
                        self.fetch_metrics(metric)
                    elif metric["type"] == "scalar_per_attribute":
                        self.fetch_metrics(metric)
                except Exception as e:
                    self.logger.error(f"Failed to validate metric {metric['name']} due to {str(e)}")    


    def start(self, nodes, scheduler_interval=60):
        self.logger.debug(f"Starting MetricsProcessor with query sets: {self.query_sets}")

        while True:
            for skill_name in ["features", "labels"]:
                self.process_metrics(nodes, skill_name)

            self.save_to_csv("combined")
            self.logger.info("Processing completed for the current cycle.")
            self.logger.info(f"Next interval begins in {scheduler_interval} seconds, waiting for the next cycle.")
            time.sleep(scheduler_interval)
