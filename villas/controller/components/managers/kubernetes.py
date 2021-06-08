import os
import threading
import kubernetes as k8s

from villas.controller.components.manager import Manager
from villas.controller.components.simulators.kubernetes import KubernetesJob


class KubernetesManager(Manager):

    def __init__(self, **args):
        super().__init__(**args)
        self.jobs = []

        self.event_watcher_thread = threading.Thread(
            target=self._run_event_watcher)

        if os.environ.get('KUBECONFIG'):
            k8s.config.load_kube_config()
        else:
            k8s.config.load_incluster_config()

        self.namespace = args.get('namespace', 'default')
        self._check_namespace(self.namespace)

        self.event_watcher_thread.setDaemon(True)
        self.event_watcher_thread.start()

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
            for ic in self.jobs:
                if ic.jobname == eo.involved_object.name:
                    if eo.reason == 'Completed':
                        ic.change_state('resetting')
                        ic.stop("nomessage")
                        ic.change_state('idle')
                    elif eo.reason == 'SuccessfulCreate':
                        ic.change_state('running')
                    else:
                        self.logger.info('Reason \'%s\' not handled for kubernetes simulator', eo.reason)

    def create(self, message):
        parameters = message.payload.get('parameters', {})
        ic = KubernetesJob(self, **parameters)
        self.logger.info('Creating new KubernetesJob component: %s', ic)

        self.add_component(ic)
        self.jobs.append(ic)

    def delete(self, message):
        parameters = message.payload.get('parameters')
        uuid = parameters.get('uuid')

        try:
            comp = self.components[uuid]

            comp.on_shutdown()
            self.remove_component(comp)

        except KeyError:
            self.logger.error('There is not component with UUID: %s', uuid)
