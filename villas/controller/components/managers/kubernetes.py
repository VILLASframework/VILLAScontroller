import os
import threading
import kubernetes as k8s

from villas.controller.components.manager import Manager
from villas.controller.components.simulators.kubernetes import KubernetesJob


class KubernetesManager(Manager):

    create_schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'properties': {
            'job': {
                '$ref': 'https://kubernetesjsonschema.dev/v1.18.1/job.json'
            },
            'schema': {
                'type': 'object',
                'additionalProperties': {
                    '$ref': 'https://json-schema.org/draft-04/schema'
                }
            }
        }
    }

    def __init__(self, **args):
        super().__init__(**args)

        self.thread_stop = threading.Event()

        self.pod_watcher_thread = threading.Thread(
            target=self._run_pod_watcher)
        self.job_watcher_thread = threading.Thread(
            target=self._run_job_watcher)
        self.event_watcher_thread = threading.Thread(
            target=self._run_event_watcher)

        if os.environ.get('KUBECONFIG'):
            k8s.config.load_kube_config()
        else:
            k8s.config.load_incluster_config()

        self.namespace = args.get('namespace', 'default')

        self._check_namespace(self.namespace)

        # self.pod_watcher_thread.start()
        # self.job_watcher_thread.start()
        # self.event_watcher_thread.start()

    def __del__(self):
        self.logger.info('Stopping Kubernetes watchers')
        self.thread_stop.set()

        if self.pod_watcher_thread.is_alive():
            self.pod_watcher_thread.join()

        if self.job_watcher_thread.is_alive():
            self.job_watcher_thread.join()

        if self.event_watcher_thread.is_alive():
            self.event_watcher_thread.join()

    def _check_namespace(self, ns):
        c = k8s.client.CoreV1Api()

        namespaces = c.list_namespace()
        for namespace in namespaces.items:
            if namespace.metadata.name == ns:
                return

        raise RuntimeError(f'Namespace {ns} does not exist')

    def _run_event_watcher(self):
        w = k8s.watch.Watch()
        c = k8s.client.CoreV1Api()

        for e in w.stream(c.list_namespaced_event,
                          namespace=self.namespace):
            eo = e.get('object')

            self.logger.info('Event: %s (reason=%s)', eo.message, eo.reason)

    def _run_pod_watcher(self):
        w = k8s.watch.Watch()
        c = k8s.client.CoreV1Api()

        for sts in w.stream(c.list_namespaced_pod,
                            namespace=self.namespace):
            stso = sts.get('object')
            typ = sts.get('type')

            self.logger.info('%s Pod: %s', typ, stso.metadata.name)

    def _run_job_watcher(self):
        w = k8s.watch.Watch()
        b = k8s.client.BatchV1Api()

        for sts in w.stream(b.list_namespaced_job,
                            namespace=self.namespace):
            stso = sts.get('object')
            typ = sts.get('type')

            self.logger.info('%s Job: %s', typ, stso.metadata.name)

    def create(self, message):
        parameters = message.payload.get('parameters', {})
        ic = KubernetesJob(self, **parameters)
        self.logger.info('Creating new KubernetesJob component: %s', ic)

        self.add_component(ic)

    def delete(self, message):
        parameters = message.payload.get('parameters')
        uuid = parameters.get('uuid')

        try:
            comp = self.components[uuid]

            comp.on_shutdown()
            self.remove_component(comp)

        except KeyError:
            self.logger.error('There is not component with UUID: %s', uuid)
