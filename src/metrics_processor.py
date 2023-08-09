import os
import yaml
import time
import inspect
import pandas as pd
from datetime import datetime

class MetricsProcessor:
    def __init__(self, prom_api, query_sets, query_mode, time_range, logger, output_format, metrics_dir="data/collection"):
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
        self.output_format = output_format
        self.query_mode = query_mode
        self.time_range= time_range

        if self.query_mode == 'range':
            self.start_time, self.end_time = self.get_time_range_from_prometheus()
            if not self.start_time or not self.end_time:
                raise Exception("Could not determine time range from Prometheus")
        else:
            self.start_time = None
            self.end_time = None


    def load_query_sets(self, query_sets):
        loaded_query_sets = {"features": [], "labels": []}
        for query_set in query_sets:
            if "features" in query_set:
                for query_file in query_set["features"]:
                    with open(query_file, "r") as f:
                        loaded_query_sets["features"].extend(yaml.safe_load(f))
            if "labels" in query_set:
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
            if self.query_mode == 'range':
                result = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time)
                if result and result[0].get("values"):
                    values = result[0]["values"]
                    self.logger.debug(f"Fetched data for {metric['name']}: {values[0]}")
                    return values[0][1]
                else:
                    self.logger.warning(f"No data returned for metric {metric['name']} in range mode.")
            else:
                result = self.prom_api.query(metric["expr"])
                if result and result[0].get("value"):
                    value = result[0]["value"]
                    self.logger.debug(f"Fetched data for {metric['name']}: {value}")
                    return value[1]
                else:
                    self.logger.warning(f"No data returned for metric {metric['name']} in instant mode.")
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
            elif metric["type"] == "boolean_per_node":
                self.process_boolean_per_node_metrics(metric)

    def process_per_node_per_attribute_metrics(self, metric):
        self.logger.debug(f"Processing per_node_per_attribute metrics for {metric['name']}.")
        try:
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)
                for item in results:
                    node_name = self.get_node_map(item['metric']['node'])
                    attribute_values = []

                    for attribute, value in item['metric'].items():
                        if attribute == "":
                            continue

                        if attribute != 'node':
                            value = value.replace('-', '_').replace('.', '_')
                            attribute_values.append(value)

                    attribute_key = '_'.join(attribute_values) if attribute_values else 'default'
                    metric_key = f"{node_name}_{attribute_key}"

                    values = [point[1] for point in item['values']]
                    if metric_key in self.row_data:
                        self.row_data[metric_key].extend(values)
                    else:
                        self.row_data[metric_key] = values

            else:
                result = self.prom_api.query(metric["expr"])
                for item in result:
                    node_name = self.get_node_map(item['metric']['node'])
                    attribute_values = []

                    for attribute, value in item['metric'].items():
                        if attribute == "":
                            continue

                        if attribute != 'node':
                            value = value.replace('-', '_').replace('.', '_')
                            attribute_values.append(value)

                    attribute_key = '_'.join(attribute_values) if attribute_values else 'default'
                    metric_key = f"{node_name}_{attribute_key}"

                    self.row_data[metric_key] = item['value'][1]

        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_scalar_metrics(self, metric):
        self.logger.debug(f"Processing scalar metrics for {metric['name']}.")
        try:
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)
                values = [point[1] for series in results for point in series['values']]
                self.row_data[metric["name"]] = values
            else:
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
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)
                
                for item in results:
                    if item['metric']['node'] == "":
                        continue

                    node_key = f"{self.get_node_map(item['metric']['node'])}_{metric['name']}"

                    # Extract values from the range results
                    values = [point[1] for point in item['values']]
                    if node_key in self.row_data:
                        self.row_data[node_key].extend(values)
                    else:
                        self.row_data[node_key] = values

            else:
                result = self.prom_api.query(metric["expr"])
                for item in result:
                    if item['metric']['node'] == "":
                        continue

                    node_key = f"{self.get_node_map(item['metric']['node'])}_{metric['name']}"
                    self.row_data[node_key] = item['value'][1]

        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for {metric['name']} with query {metric['expr']} due to {str(e)}")

    def process_boolean_per_node_metrics(self, metric):
        self.logger.debug(f"Processing boolean_per_node metrics for {metric['name']}.")
        try:
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)

                for item in results:
                    if item['metric']['node'] == "":
                        continue

                    node_name = self.get_node_map(item['metric']['node'])
                    metric_name = metric['name']

                    # Extract values from the range results
                    values = ['green' if point[1] == '0' else metric['label'] for point in item['values']]
                    metric_key = f"{node_name}_{metric_name}"

                    if metric_key in self.row_data:
                        self.row_data[metric_key].extend(values)
                    else:
                        self.row_data[metric_key] = values

            else:
                result = self.prom_api.query(metric["expr"])

                for item in result:
                    if item['metric']['node'] == "":
                        continue

                    node_name = self.get_node_map(item['metric']['node'])
                    metric_name = metric['name']
                    value = item["value"][1]
                    self.row_data[f"{node_name}_{metric_name}"] = 'green' if value == '0' else metric['label']

        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for {metric['name']} with query {metric['expr']} due to {str(e)}")

    def process_boolean_metrics(self, metric):
        self.logger.debug(f"Processing boolean metrics for {metric['name']}.")
        try:
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)
                # Extract values from the range results
                values = [point[1] for series in results for point in series['values']]
                self.row_data[metric["name"]] = values
            else:
                result = self.prom_api.query(metric["expr"])
                if result:
                    value = result[0]["value"][1]
                    self.row_data[metric["name"]] = value
        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for query {metric['expr']} due to {str(e)}")

    def process_scalar_per_attribute_metrics(self, metric):
        self.logger.debug(f"Processing scalar_per_attribute metrics for {metric['name']}.")
        try:
            if self.query_mode == "range":
                results = self.prom_api.query_range(metric["expr"], start=self.start_time, end=self.end_time, step=self.time_range)

                for item in results:
                    attribute_values = []

                    for attribute, value in item['metric'].items():
                        if attribute == "":
                            continue

                    # Join all attribute values with underscore to create final attribute key
                    attribute_key = '_'.join(attribute_values) if attribute_values else 'default'
                    metric_key = f"{metric['name']}_{attribute_key}"

                    # Extract values from the range results
                    values = [point[1] for point in item['values']]
                    if metric_key in self.row_data:
                        self.row_data[metric_key].extend(values)
                    else:
                        self.row_data[metric_key] = values

            else:
                result = self.prom_api.query(metric["expr"])

                for item in result:
                    attribute_values = []

                    for attribute, value in item['metric'].items():
                        if attribute == "":
                            continue

                    # Join all attribute values with underscore to create final attribute key
                    attribute_key = '_'.join(attribute_values) if attribute_values else 'default'
                    metric_key = f"{metric['name']}_{attribute_key}"
                    self.row_data[metric_key] = item['value'][1]

        except Exception as e:
            self.logger.error(f"[{inspect.stack()[0][3]}] Failed to fetch data for {metric['name']} with query {metric['expr']} due to {str(e)}")

    
    def commit_to_memory(self):
        self.logger.debug(f"Saving data to DataFrame.")

        # Convert row_data to a list of dictionaries for DataFrame conversion
        data = []
        keys = self.row_data.keys()
        max_len = max(len(v) if isinstance(v, list) else 1 for v in self.row_data.values())
        
        for i in range(max_len):
            row = {}
            for key in keys:
                val = self.row_data[key]
                if isinstance(val, list):
                    row[key] = val[i] if i < len(val) else None  # use None if index exceeds list length
                else:
                    row[key] = val
            data.append(row)

        df = pd.DataFrame(data)
        self.df = pd.concat([self.df, df])

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

    def save_to_csv(self, collection):
        self.logger.debug(f"Saving data to DataFrame for {collection}.")

        # Create the directory if it doesn't exist
        if not os.path.exists(self.metrics_dir):
            os.makedirs(self.metrics_dir)

        # Create the filename
        filename = f'{self.metrics_dir}/metrics_{collection}_{self.timestamp}.csv'

        self.df.to_csv(filename)

        self.logger.debug(f"Saved {collection} DataFrame to {filename}")

    def get_time_range_from_prometheus(self):
        try:
            response = self.prom_api.get_status('tsdb')

            self.logger.debug(f"Prometheus tsdb status response: {response}")

            if 'data' in response:
                data = response['data']
                head_stats = data.get('headStats', {})
                start_time = head_stats.get('minTime', None)
                end_time = head_stats.get('maxTime', None)

                if start_time and end_time:
                    # Convert milliseconds to seconds since Python datetime uses seconds
                    start_time = datetime.fromtimestamp(start_time / 1000)
                    end_time = datetime.fromtimestamp(end_time / 1000)
                    return start_time, end_time
                else:
                    self.logger.error("Could not extract minTime and maxTime from Prometheus response.")
                    return None, None
            else:
                self.logger.error(f"Failed to fetch time range from Prometheus.")
                return None, None
        except Exception as e:
            self.logger.error(f"Error fetching time range from Prometheus: {e}")
            return None, None

    def validate_queries(self):
        for item in ["features", "labels"]:
            for metric in self.query_sets[item]:
                try:
                    self.fetch_metrics(metric)
                except Exception as e:
                    self.logger.error(f"[{inspect.stack()[0][3]}] Failed to validate metric {metric['name']} due to {str(e)}")    

    def start(self, scheduler_interval=0):
        self.logger.debug(f"Starting MetricsProcessor with query sets: {self.query_sets}")

        # If query_mode is set to range, the script should process the time range specified by time_range
        if self.query_mode == 'range':
            self.reset_row_data()  # reset array to prevent data leaking between runs
            for skill_name in ["features", "labels"]:
                self.process_metrics(skill_name)
            
            self.commit_to_memory()
            if self.output_format == "parquet":
                self.save_to_parquet("combined")
            elif self.output_format == "csv":
                self.save_to_csv("combined")
            else:
                self.logger.error(f"Unsupported output format: {self.output_format}. Data not saved.")
            
            self.logger.info("Processing completed for the time range specified.")
            return  # Exit the function

        # If query_mode is set to another value (e.g., instant), the script should repeatedly execute in intervals
        print(f"MetricsProcessor with interval={scheduler_interval}")

        while True:
            self.reset_row_data() # reset array to prevent data leaking between runs

            for skill_name in ["features", "labels"]:
                self.process_metrics(skill_name)

            self.commit_to_memory()
            if self.output_format == "parquet":
                self.save_to_parquet("combined")
            elif self.output_format == "csv":
                self.save_to_csv("combined")
            else:
                self.logger.error(f"Unsupported output format: {self.output_format}. Data not saved.")
    
            self.logger.info("Processing completed for the current cycle.")
            self.logger.info(f"Next interval begins in {scheduler_interval} seconds, waiting for the next cycle.")
            if (scheduler_interval == 0):
                # When interval == 0 then run only once
                break
            else:
                time.sleep(scheduler_interval)
