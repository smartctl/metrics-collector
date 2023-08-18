# CREDITS & REFERENCES

## Credits

Some of the PromQL queries used in the `feature-definitons.yaml` and `labels-definition.yaml` are inspired, derived or adapted from work on the open-source OpenShift community.

* [Cluster Monitoring Operator - prometheus-rule.yaml](https://github.com/openshift/cluster-monitoring-operator/blob/master/assets/cluster-monitoring-operator/prometheus-rule.yaml)
* [etcdGRPCRequestsSlow](https://github.com/openshift/runbooks/blob/master/alerts/cluster-etcd-operator/etcdGRPCRequestsSlow.md)
* [ExtremelyHighIndividualControlPlaneCPU](https://github.com/openshift/runbooks/blob/master/alerts/cluster-kube-apiserver-operator/ExtremelyHighIndividualControlPlaneCPU.md)
* [KubeAPIErrorBudgetBurn](https://github.com/openshift/runbooks/blob/master/alerts/cluster-kube-apiserver-operator/KubeAPIErrorBudgetBurn.md)
* [OpenShift cluster monitoring operator](https://github.com/openshift/cluster-monitoring-operator/blob/master/manifests/0000_50_cluster-monitoring-operator_04-config.yaml)
* [OpenShift etcd Performance Metrics](https://github.com/openshift/cluster-etcd-operator/blob/master/docs/performance-metrics.md)
* [Recommended etcd practices](https://github.com/openshift/openshift-docs/blob/main/modules/recommended-etcd-practices.adoc)

## References

This work uses techniques or formulas from the following sources

* [Analysing Prometheus Metrics in Pandas](https://ricardorocha.io/blog/prometheus-metrics-in-pandas/)
* [Analyze Prometheus Metrics Like a Data Scientist](https://promcon.io/2017-munich/slides/analyze-prometheus-metrics-like-a-data-scientist.pdf)
    * [PromCon 2017: Analyze Prometheus Metrics like a Data Scientist - Georg Öttl](https://www.youtube.com/watch?v=aUOgPdaXOwQ)
* [A deep dive into the four types of Prometheus Metrics](https://www.timescale.com/blog/four-types-prometheus-metrics-to-collect/)
* [Interpreting Prometheus Metrics for Linux disk IO utilization](https://brian-candler.medium.com/interpreting-prometheus-metrics-for-linux-disk-i-o-utilization-4db53dfedcfc)
* [pandas-data-storage-compare.py](https://gist.github.com/RobMulla/738491f7bf7cfe79168c7e55c622efa5) Comparing data storage size
