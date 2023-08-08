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

        response = requests.get(
            self.url + "/api/v1/query",
            params=params,
            headers=self.headers,
            verify=False  # Ignore SSL errors if the Prometheus instance uses self-signed SSL
        )

        response.raise_for_status()
        return response.json()["data"]["result"]
