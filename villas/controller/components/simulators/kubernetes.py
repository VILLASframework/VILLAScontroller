import json
import signal
from copy import deepcopy
import collections

import kubernetes as k8s

from villas.controller.components.simulator import Simulator


def merge(dict1, dict2):
    ''' Return a new dictionary by merging two dictionaries recursively. '''

    result = deepcopy(dict1)

    for key, value in dict2.items():
        if isinstance(value, collections.Mapping):
            result[key] = merge(result.get(key, {}), value)
        elif value is None:
            del result[key]
        else:
            result[key] = deepcopy(dict2[key])

    return result


class KubernetesJob(Simulator):

    def __init__(self, manager, **args):
        super().__init__(**args)

        self.manager = manager

        # Job template which can be overwritten via start parameter
        self.job = args.get('properties', {}).get('job')
        self.name = self.job['metadata']['name']

    def __del__(self):
        pass

    def _prepare_job(self, job, parameters):

        cm = self._create_config_map(parameters)

        v = k8s.client.V1Volume(
            name='parameters',
            config_map=k8s.client.V1ConfigMapVolumeSource(
                name=cm.metadata.name
            )
        )

        vm = k8s.client.V1VolumeMount(
            name='parameters',
            mount_path='/config/',
            read_only=True
        )

        env = k8s.client.V1EnvVar(
            name='VILLAS_PARAMETERS_FILE',
            value='/config/parameters.json'
        )

        containerList = []
        for cont in job['spec']['template']['spec']['containers']:
            containerList.append(k8s.client.V1Container(
                image=cont['image'],
                name=cont['name'],
                command=cont['command'],
                volume_mounts=[vm],
                env=[env]
            ))

        jobSpec = k8s.client.V1JobSpec(
            template=k8s.client.V1PodTemplateSpec(
                spec=k8s.client.V1PodSpec(
                    containers=containerList,
                    volumes=[v],
                    restart_policy=job['spec']['template']['spec']['restartPolicy']
                )
            ),
            active_deadline_seconds=job['spec']['activeDeadlineSeconds'],
            backoff_limit=job['spec']['backoffLimit'],
            ttl_seconds_after_finished=job['spec']['ttlSecondsAfterFinished'],
        )

        metaData = k8s.client.V1ObjectMeta(
            name=None,
            generate_name=job['metadata']['name'] + '-',
            labels={
            'controller': 'villas',
            'controller-uuid': self.manager.uuid,
            'uuid': self.uuid
            }
        )

        return k8s.client.V1Job(
            api_version=job['apiVersion'],
            kind=job['kind'],
            metadata=metaData,
            spec=jobSpec
        )

    def _create_config_map(self, parameters):
        c = k8s.client.CoreV1Api()

        self.cm = k8s.client.V1ConfigMap(
            metadata=k8s.client.V1ObjectMeta(
                generate_name='job-parameters-'
            ),
            data={
                'parameters.json': json.dumps(parameters)
            }
        )

        return c.create_namespaced_config_map(
            namespace=self.manager.namespace,
            body=self.cm
        )

    def start(self, message):
        job = message.payload.get('job', {})
        parameters = message.payload.get('parameters', {})

        job = merge(self.job, job)
        self.name = job['metadata']['name']
        v1job = self._prepare_job(self.job, parameters)

        b = k8s.client.BatchV1Api()
        self.job = b.create_namespaced_job(
            namespace=self.manager.namespace,
            body=v1job)

    def stop(self, message):
        b = k8s.client.BatchV1Api()
        self.job = b.delete_namespaced_job(
            namespace=self.manager.namespace,
            name=self.name)

    def _send_signal(self, sig):
        c = k8s.client.api.CoreV1Api()
        resp = k8s.stream.stream(c.connect_get_namespaced_pod_exec,
                                 self.name, self.manager.namespace,
                                 command=['kill', f'-{sig}', '1'],
                                 stderr=False, stdin=False,
                                 stdout=False, tty=False)

        self.logger.debug('Send signal %d to container: %s', sig, resp)

    def pause(self, message):
        self._send_signal(signal.SIGSTOP)

    def resume(self, message):
        self._send_signal(signal.SIGCONT)
