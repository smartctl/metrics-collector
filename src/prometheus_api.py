import requests
import urllib3
import time
import logging

class PrometheusAPI:
    def __init__(self, url, token, logger=None):
        self.url = url
        self.token = token
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.headers = {"Authorization": "Bearer " + token}
        self.logger = logger if logger else logging.getLogger(__name__)

    def query(self, query):
        params = {
            "query": str(query),
            "time": round(time.time())
        }

        self.logger.debug(f"Executing query: {params['query']} at time: {params['time']}")

        response = requests.get(
            self.url + "/api/v1/query",
            params=params,
            headers=self.headers,
            verify=False  # Ignore SSL errors if the Prometheus instance uses self-signed SSL
        )

        response.raise_for_status()
        self.logger.debug("Query executed successfully.")
        return response.json()["data"]["result"]

    def query_range(self, query, start, end, step="15m"):
        start_timestamp = round(start.timestamp())
        end_timestamp = round(end.timestamp())

        params = {
            "query": str(query),
            "start": start_timestamp,
            "end": end_timestamp,
            "step": step
        }

        self.logger.debug(f"Executing range query: {params['query']} from {params['start']} to {params['end']} with step: {params['step']}")
        response = requests.get(
            self.url + "/api/v1/query_range",
            params=params,
            headers=self.headers,
            verify=False  # Ignore SSL errors if the Prometheus instance uses self-signed SSL
        )

        response.raise_for_status()
        self.logger.debug("Range query executed successfully.")
        return response.json()["data"]["result"]

    def get_status(self, status_type):
        endpoint = f"{self.url}/api/v1/status/{status_type}"
        self.logger.debug(f"Fetching {status_type} status from Prometheus.")
        response = requests.get(
            endpoint, 
            headers=self.headers,
            verify=False  # Ignore SSL errors if the Prometheus instance uses self-signed SSL
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch {status_type} status from Prometheus. Status code: {response.status_code}")
        self.logger.info(f"Fetched {status_type} status successfully.")
        return response.json()
