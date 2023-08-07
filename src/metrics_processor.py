import csv
import os
import yaml
import time
import inspect
import pandas as pd

class MetricsProcessor:
    def __init__(self, prom_api, query_sets, logger, metrics_dir="data/collection"):
        self.prom_api = prom_api
        self.logger = logger
        self.metrics_dir = metrics_dir
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)
        self.query_sets = self.load_query_sets(query_sets)
        self.df = pd.DataFrame()
        self.timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.node_mapping = {}
        self.row_data = {}
        self.reset_row_data()
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

    def reset_row_data(self):
        self.row_data={"run_id":self.timestamp}

    def fetch_metrics(self, metric):
        self.logger.debug(f"Validating entry format.")
        try:
            if metric.get("name") is None:
                raise Exception(f"Missing the 'name' key",f"{metric}")
            if metric.get("type") is None:
                raise Exception(f"Entry '{metric['name']}' missing the 'type' key")        
            if metric.get("expr") is None:
                raise Exception(f"Entry '{metric['name']}' missing the 'expr' key")    
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Invalid entry. {str(e)}")
            return None
        
        self.logger.debug(f"Validating queries.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"]
                self.logger.debug(f"Fetched data for {metric['name']}: {value}")
                return value[1]
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for metric {metric['name']} due to {str(e)}")
            return None

    def process_metrics(self, skill_name):
        for metric in self.query_sets[skill_name]:
            # validate the entry has the required keys
            self.logger.debug(f"Validating entry format for {metric}")
            try:
                if metric.get("name") is None:
                    raise Exception(f"Missing the 'name' key",f"{metric}")
                if metric.get("type") is None:
                    raise Exception(f"Entry '{metric['name']}' missing the 'type' key")        
                if metric.get("expr") is None:
                    raise Exception(f"Entry '{metric['name']}' missing the 'expr' key")    
            except Exception as e:
                self.logger.error(f"[{inspect.stack()[0][3]}] Invalid entry. {str(e)}")
                return None

            self.logger.debug(f"Processing metric: {metric['name']}, type: {metric['type']}")
            if metric["type"] == "scalar":
                self.process_scalar_metrics(metric)
            elif metric["type"].endswith("per_node"):
                self.process_per_node_metrics(metric)
            elif metric["type"].endswith("per_node_per_attribute"):
                self.process_per_node_per_attribute_metrics(metric)
            elif metric["type"] == "boolean":
                self.process_boolean_metrics(metric)
            elif metric["type"] == "scalar_per_attribute":
                self.process_scalar_per_attribute_metrics(metric)

    def process_per_node_per_attribute_metrics(self, metric):
        self.logger.debug(f"Processing per_node_per_attribute metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric['expr'])
            for item in result:
                node_name = self.get_node_map(item['metric']['node'])
                attribute_values = []
                for attribute, value in item['metric'].items():
                    if attribute == "":
                            continue
                    # Exclude 'node' attribute because we already consider node in row_data key
                    if attribute != 'node':
                        value = value.replace('-','_').replace('.','_')
                        attribute_values.append(value)
                # Join all attribute values with underscore to create final attribute name
                attribute_key = '_'.join(attribute_values) if attribute_values else 'default'              
                self.row_data[f"{node_name}_{attribute_key}"] = item['value'][1]
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_scalar_metrics(self, metric):
        self.logger.debug(f"Processing scalar metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"][1]
                self.row_data[metric["name"]] = value
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def get_node_map(self, node_name):
        return self.node_mapping.setdefault(node_name,"node"+str(len(self.node_mapping)+1))

    def process_per_node_metrics(self, metric):
        self.logger.debug(f"Processing per_node metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric['expr'])
            for item in result:
                if item['metric']['node'] == "":
                    continue
                self.row_data[f"{self.get_node_map(item['metric']['node'])}_{metric['name']}"] = item['value'][1]
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for {metric['name']} with query {metric['expr']} due to {str(e)}")

    def process_boolean_per_node_metrics(self, metric):
        self.logger.debug(f"Processing boolean_per_node metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric['expr'])
            for item in result:
                if item['metric']['node'] == "":
                    continue
                node_name = self.get_node_map(item['metric']['node'])
                metric_name = metric['name']
                value = result[0]["value"][1]
                self.row_data[f"{node_name}_{metric_name}"] = 'green' if value == '0' else metric['label']
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_boolean_metrics(self, metric):
        self.logger.debug(f"Processing boolean metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                value = result[0]["value"][1]
                self.row_data[metric["name"]] = value
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_scalar_per_attribute_metrics(self, metric):
        self.logger.debug(f"Processing scalar_per_attribute metrics for {metric['name']}.")
        try:
            result = self.prom_api.query(metric["expr"])
            if result:
                for res in result:
                    # Prepare list to gather all attribute values
                    attribute_values = []
                    for attribute, value in res['metric'].items():
                        if attribute == "":
                            continue
                        if attribute == 'instance':
                            value=value.split(":")[0]
                        value = value.replace('-','_').replace('.','_')
                        attribute_values.append(value)
                    # Join all attribute values with underscore to create final attribute name
                    attribute = '_'.join(attribute_values) if attribute_values else 'default'
                    value = res["value"][1]
                    self.row_data[f"{metric['name']}_{attribute}"] = value
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")
    
    def commit_to_memory(self):
        self.logger.debug(f"Saving data to DataFrame.")

        df = pd.DataFrame(self.row_data,index=[0])
        self.df=pd.concat([self.df,df])

        self.logger.debug(f"Appended {df.shape} DataFrame to class. Shape in memory {self.df.shape}")

    def save_to_parquet(self, collection):
        self.logger.debug(f"Saving data to DataFrame for {collection}.")

        # Create the directory if it doesn't exist
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)

        # Create the filename
        filename = f'{self.metrics_dir}/metrics_{collection}_{self.timestamp}.parquet'

        self.df.to_parquet(filename, compression="snappy")

        self.logger.debug(f"Saved {collection} DataFrame to {filename}")

    def validate_queries(self):
        for item in ["features", "labels"]:
            for metric in self.query_sets[item]:
                try:
                    self.fetch_metrics(metric)
                except Exception as e:
                    self.logger.error(f"[{inspect.stack()[0][3]}] Failed to validate metric {metric['name']} due to {str(e)}")    

    def start(self, scheduler_interval=0):
        self.logger.debug(f"Starting MetricsProcessor with query sets: {self.query_sets}")

        import sys
        print(f"MetricsProcessor with interval={scheduler_interval}")

        while True:
            self.reset_row_data() # reset array to prevent data leaking between runs

            for skill_name in ["features", "labels"]:
                self.process_metrics(skill_name)

            self.commit_to_memory()
            self.save_to_parquet("combined")
            self.logger.info("Processing completed for the current cycle.")
            self.logger.info(f"Next interval begins in {scheduler_interval} seconds, waiting for the next cycle.")
            if (scheduler_interval == 0):
                break
            else:
                time.sleep(scheduler_interval)
