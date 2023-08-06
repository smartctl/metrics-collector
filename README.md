# Matrics Collector

A collector of Prometheus metrics for data anisys.

## Usage

- Setup a Python Virtual Environment
```bash
# Create a Python Virtual Environment
python3 -m venv venv

# Activate the virtual environment
source ./venv/bin/activate

# Install Python libraries in virtual environment
pip install -r requirements.txt
```

- Update `config.yaml` to match your environment. Example:

```yaml
collector:
  interval: 30 # frequency to execute a collection cycle (seconds)

prometheus:
  url: "https://prometheus-k8s-openshift-monitoring.apps.<clusterName>.<baseDomain>"
  token: "YOUR_TOKEN_HERE" # See Token section
  query_sets:
    - name: base
      features:
        - "querysets/ocp-platform/features-definition.yaml"
      labels:
        - "querysets/ocp-platform/labels-definition.yaml"
```
- Execute the collector `python main.py` and collect for the desired time.
  - Press Ctrl-C to break or stop collection
  - A parquet file will be written to data/collection 
    ```
    data/
    └── collection
        └── metrics_combined_20230806-135903.parquet
    ```
- Load the collection file for data analysis using the Pandas library
  ```python
  import pandas as pd
  fname="data/collection/metrics_combined_20230806-135903.parquet"
  df=pd.read_parquet(fname)
  df.head()
  ```

### Obtaining Prometheus Token

- [OCP 4.11 and onwards](https://access.redhat.com/solutions/6749541) requires the creation of a Secret artificat on the openshift-monitoring namespace
```bash
# Create secret for Prometheus token for the app
oc create -f ./manifests/00-prometheus-api-token.yaml

# Retrieve the token
TOKEN=`oc -n openshift-monitoring extract secret/prometheus-api-token --to=- --keys=token`

# To see and copy the token
echo $TOKEN
```

- Obtain Prometheus URL
``` bash
# Retrieve the route for the Prometheus endpoing 
PROMETHEUS_URL=$(oc get route -n openshift-monitoring prometheus-k8s -o jsonpath="{.status.ingress[0].host}")

# To see and copy the Prometheus URL
echo $PROMETHEUS_URL
```

- To test if token and URL are working
```bash
# Query for allerts
curl -sk -H "Authorization: Bearer $TOKEN" https://$PROMETHEUS_URL/api/v1/alerts 
```
