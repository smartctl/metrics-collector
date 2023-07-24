docker stop kraken
docker rm kraken
docker run --name=kraken --net=host \
    -v ${HOME}/.kube/config:/root/.kube/config:Z \
    -v ${PWD}/config_ocp.yaml:/root/kraken/config/config.yaml:Z \
    -v ${PWD}/config/kube_burner.yaml:/root/kraken/config/kube_burner.yaml:Z \
    -v ${PWD}/config/metrics-aggregated.yaml:/root/kraken/config/metrics-aggregated.yaml:Z \
    -d quay.io/redhat-chaos/krkn:latest