import requests
import urllib3
import time

class PrometheusAPI:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.headers = {"Authorization": "Bearer " + token}

    def query(self, query):
        params = {
            "query": query,
            "time": round(time.time())
        }
        response = requests.get(
            self.url + "/api/v1/query",
            params=params,
            headers=self.headers,
            verify=False  # If the Prometheus instance uses self-signed SSL
        )
        response.raise_for_status()
        return response.json()["data"]["result"]
