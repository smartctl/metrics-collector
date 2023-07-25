import csv
import requests
import yaml
import urllib3
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import time
from kubernetes import client, config

# Create a custom logger
logger = logging.getLogger(__name__)

# Set the level of logger to INFO
logger.setLevel(logging.INFO)

# Create handlers
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

def get_app_names():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    namespace = "openshift-monitoring"
    ret = v1.list_namespaced_pod(namespace=namespace)
    return [i.metadata.name for i in ret.items]

# Load your YAML file
with open("queries1.yaml", "r") as f:
    queries = yaml.safe_load(f)
    logger.info("Successfully loaded the YAML file.")

# Setup Prometheus connection
prometheus_url = "https://prometheus-k8s-openshift-monitoring.apps.hubztp.telco.ocp.run"
token = "sha256~fiNsYzfBum-76aC6hS3auH_kNzG3xkYqrSsKXsiY3Lc"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger.info("Disabled urllib3 warnings.")

headers = {
    "Authorization": "Bearer " + token,
}

def fetch_data(namespace):
    app_names = get_app_names()
    for app_name in app_names:
        logger.info(f"Fetching data for app: {app_name}, namespace: {namespace}.")
        # Initialize a dictionary that maps timestamps to lists of metric values
        data = {}
        # Fetch the data for each query
        for query in queries:
            # formatted_query = query["query"].format(namespace=namespace, app_name=app_name)
            formatted_query = query["query"].replace("{namespace}", namespace).replace("{app_name}", app_name)


            params = {
                "query": formatted_query,
                "time": round(time.time())
            }
            response = requests.get(
                prometheus_url + "/api/v1/query",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                verify=False  # If the Prometheus instance uses self-signed SSL
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                logger.error(f"HTTP error occurred: {err}")
                logger.error(f"Failed to fetch data for query {params['query']}.")
                continue  # skip to the next query or app_name

            result = response.json()["data"]["result"]
            if result:
                value = result[0]["value"]
                timestamp = value[0]
                if timestamp not in data:
                    data[timestamp] = [app_name] + ['0.0']*len(queries)
                data[timestamp][queries.index(query)+1] = value[1]

        # Prepare data for writing to CSV
        rows = [[timestamp] + values for timestamp, values in sorted(data.items())]

        # Write the data to CSV
        with open("metrics.csv", "a", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["timestamp", "app_name"] + [q["metricName"] for q in queries])
            for row in rows:
                writer.writerow(row)
                logger.info(f"Appended data for timestamp {row[0]} to CSV file.")


# Schedule the task to run every 10 seconds (or whatever your desired interval is)
scheduler = BackgroundScheduler()

namespace = "openshift-monitoring"  # Substitute with your namespace

seconds=100
scheduler.add_job(fetch_data, 'interval', seconds=seconds, args=[namespace])
logger.info(f"Scheduled the job to run every { seconds } seconds.")

# Start the scheduler
logger.info("Starting the scheduler.")
fetch_data(namespace)
scheduler.start()

# Keep the script running
while True:
    time.sleep(1)
