import csv
import requests
import yaml
import urllib3
from datetime import datetime, timedelta
import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

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

# Load your YAML file
with open("queries.yaml", "r") as f:
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

# Prepare to fetch the data
csv_headers = ["timestamp"] + [q["metricName"] for q in queries]

# Initialize a dictionary that maps timestamps to lists of metric values
data = {}

# Fetch the data for each query
def fetch_data():
    logger.info("Fetching data from Prometheus.")
    for query in queries:
        response = requests.get(
            prometheus_url + "/api/v1/query",
            params={"query": query["query"], "time": round(datetime.now().timestamp())},
            headers=headers,
            verify=False  # If the Prometheus instance uses self-signed SSL
        )
        response.raise_for_status()
        logger.info(f"Fetched data for query {query['query']}.")

        result = response.json()["data"]["result"]
        if result:
            value = result[0]["value"]
            timestamp = value[0]
            # If this timestamp is new, initialize it with a list of '0.0' values
            if timestamp not in data:
                data[timestamp] = ['0.0']*len(queries)
                # Add the metric value to the list at the position determined by the order of queries in the YAML file
                data[timestamp][csv_headers.index(query["metricName"])-1] = value[1]

                # Prepare data for writing to CSV
                rows = [[timestamp] + values for timestamp, values in data.items()]

                # Append the new data to CSV
                with open("metrics.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(rows[-1])
                logger.info(f"Appended data for timestamp {timestamp} to CSV file.")

# Schedule the task to run every 10 seconds (or whatever your desired interval is)
seconds=10
scheduler.add_job(fetch_data, 'interval', seconds=seconds)
logger.info("Scheduled the job to run every %.f seconds.", seconds)

# Start the scheduler
logger.info("Starting the scheduler.")
scheduler.start()
