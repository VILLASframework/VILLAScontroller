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
        self.jobdict = args.get('properties', {}).get('job')
        self.jobname = self.jobdict['metadata']['name']

    def __del__(self):
        pass

    def _prepare_job(self, job, payload):

        cm = self._create_config_map(payload)

        v = k8s.client.V1Volume(
            name='payload',
            config_map=k8s.client.V1ConfigMapVolumeSource(
                name=cm.metadata.name
            )
        )

        vm = k8s.client.V1VolumeMount(
            name='payload',
            mount_path='/config/',
            read_only=True
        )

        env = k8s.client.V1EnvVar(
            name='VILLAS_PAYLOAD_FILE',
            value='/config/payload.json'
        )

        containerList = []
        for cont in job['spec']['template']['spec']['containers']:
            containerList.append(k8s.client.V1Container(
                image=cont['image'],
                name=cont['name'],
                command=cont.get('command'),
                volume_mounts=[vm],
                env=[env]
            ))

        restartPolicy = job['spec']['template']['spec']['restartPolicy']
        jobSpec = k8s.client.V1JobSpec(
            template=k8s.client.V1PodTemplateSpec(
                spec=k8s.client.V1PodSpec(
                    containers=containerList,
                    volumes=[v],
                    restart_policy=restartPolicy
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

    def _create_config_map(self, payload):
        c = k8s.client.CoreV1Api()

        self.cm = k8s.client.V1ConfigMap(
            metadata=k8s.client.V1ObjectMeta(
                generate_name='job-payload-'
            ),
            data={
                'payload.json': json.dumps(payload)
            }
        )

        return c.create_namespaced_config_map(
            namespace=self.manager.namespace,
            body=self.cm
        )

    def start(self, message):
        job = message.payload.get('job', {})
        payload = message.payload

        job = merge(self.jobdict, job)
        self.jobname = job['metadata']['name']
        v1job = self._prepare_job(self.jobdict, payload)

        b = k8s.client.BatchV1Api()
        self.job = b.create_namespaced_job(
            namespace=self.manager.namespace,
            body=v1job)
        self.jobname = self.job.metadata.name

    def stop(self, message):
        # self.change_state('stopping')
        b = k8s.client.BatchV1Api()
        body = k8s.client.V1DeleteOptions(propagation_policy='Background')
        self.job = b.delete_namespaced_job(
            namespace=self.manager.namespace,
            name=self.jobname,
            body=body)

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
