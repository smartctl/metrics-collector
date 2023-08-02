from kubernetes import client, config
import logging

class KubernetesAPI:
    def __init__(self, logger=None):
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.logger = logger if logger else logging.getLogger(__name__)

    def get_pod_names(self, namespace):
        ret = self.v1.list_namespaced_pod(namespace=namespace)
        return [i.metadata.name for i in ret.items]

    def get_app_names(self, namespace):
        ret_statefulset = self.apps_v1.list_namespaced_stateful_set(namespace)
        ret_deployment = self.apps_v1.list_namespaced_deployment(namespace)
        ret_daemonset = self.apps_v1.list_namespaced_daemon_set(namespace)
        return [i.metadata.name for i in ret_statefulset.items + ret_deployment.items + ret_daemonset.items]

    def get_all_namespaces(self):
        ret = self.v1.list_namespace()
        return [i.metadata.name for i in ret.items]

    def get_node_count(self):
        try:
            nodes = self.v1.list_node()
            return len(nodes.items)
        except Exception as e:
            self.logger.error(f"Failed to fetch node count due to {str(e)}")
            return None
