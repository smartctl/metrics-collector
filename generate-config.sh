# Create secret for Prometheus token for the app
oc apply -f ./manifests/00-prometheus-api-token.yaml

# Retrieve the token
export TOKEN=`oc -n openshift-monitoring extract secret/prometheus-api-token --to=- --keys=token`

# To see and copy the token
echo "TOKEN:" $TOKEN

# Retrieve the route for the Prometheus endpoing 
export PROMETHEUS_URL=$(oc get route -n openshift-monitoring prometheus-k8s -o jsonpath="{.status.ingress[0].host}")

# To see and copy the Prometheus URL
echo "PROMETHEUS_URL:" $PROMETHEUS_URL

envsubst < config-template.yaml 