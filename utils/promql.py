import csv
import requests
import yaml
import urllib3
from datetime import datetime, timedelta

# Load your YAML file
with open("queries.yaml", "r") as f:
    queries = yaml.safe_load(f)

# Setup Prometheus connection
prometheus_url = "https://prometheus-k8s-openshift-monitoring.apps.hubztp.telco.ocp.run"
token = "sha256~fiNsYzfBum-76aC6hS3auH_kNzG3xkYqrSsKXsiY3Lc"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "Authorization": "Bearer " + token,
}

# Prepare to fetch the data
csv_headers = ["timestamp"] + [q["metricName"] for q in queries]

# Initialize a dictionary that maps timestamps to lists of metric values
data = {}

# Fetch the data for each query
for query in queries:
    response = requests.get(
        prometheus_url + "/api/v1/query",
        params={"query": query["query"], "time": round(datetime.now().timestamp())},
        headers=headers,
        verify=False  # If the Prometheus instance uses self-signed SSL
    )
    response.raise_for_status()

    result = response.json()["data"]["result"]
    if result:
        value = result[0]["value"]
        timestamp = value[0]
        # If this timestamp is new, initialize it with a list of None values
        if timestamp not in data:
            data[timestamp] = [None]*len(queries)
        # Add the metric value to the list at the position determined by the order of queries in the YAML file
        data[timestamp][csv_headers.index(query["metricName"])-1] = value[1]


# Prepare data for writing to CSV
rows = [[timestamp] + values for timestamp, values in data.items()]

# Write the data to CSV
with open("metrics.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(csv_headers)
    writer.writerows(rows)
