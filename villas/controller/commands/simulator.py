import kombu
import socket
import json
import sys
import logging

from villas.controller.command import Command

LOGGER = logging.getLogger(__name__)


def _get_parameters(args):
    parameters = {}

    try:
        if args.parameters is not None:
            parameters.update(json.loads(args.parameters))
        if args.parameters_file is not None:
            with open(args.parameters_file) as f:
                parameters.update(json.load(f))

        return parameters
    except OSError as e:
        LOGGER.error('Failed to open parameter file: %s',
                      e.strerror)
    except json.JSONDecodeError as e:
        LOGGER.error('Failed to parse parameters: %s at line %d column %d',
                     e.msg, e.lineno, e.colno)


class SimulatorCommand(Command):

    @staticmethod
    def run(connection, args):
        pass

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('simulator',
                                       help='Send control command to simulator')  # noqa F501

        filt = parser.add_argument_group('Filter simulators')
        filt.add_argument('-r', '--realm')
        filt.add_argument('-c', '--category')
        filt.add_argument('-t', '--type')
        filt.add_argument('-u', '--uuid')

        sim_subparsers = parser.add_subparsers(
            title='action',
            metavar='ACTION',
            help='Available simulator commands')
        sim_subparsers.required = True
        sim_subparsers.dest = 'command'

        SimulatorStartCommand.add_parser(sim_subparsers)
        SimulatorStopCommand.add_parser(sim_subparsers)
        SimulatorPauseCommand.add_parser(sim_subparsers)
        SimulatorResumeCommand.add_parser(sim_subparsers)
        SimulatorPingCommand.add_parser(sim_subparsers)
        SimulatorResetCommand.add_parser(sim_subparsers)
        SimulatorCreateCommand.add_parser(sim_subparsers)
        SimulatorDeleteCommand.add_parser(sim_subparsers)

    @staticmethod
    def get_headers(args):
        headers = {'x-match': 'any'}

        if args.realm:
            headers['realm'] = args.realm

        if args.uuid:
            headers['uuid'] = args.uuid

        if args.category:
            headers['category'] = args.category

        if args.type:
            headers['type'] = args.type

        if len(headers) <= 1:
            headers['x-match'] = 'all'

        return headers


class SimulatorPingCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('ping', help='Ping a remote simulator')
        parser.set_defaults(func=SimulatorPingCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas',
                                  type='headers',
                                  durable=True)

        producer = kombu.Producer(channel, exchange=exchange)
        consumer = kombu.Consumer(channel,
                                  queues=kombu.Queue(
                                      exchange=exchange,
                                      durable=False
                                  ),
                                  on_message=SimulatorPingCommand.on_message)

        message = {'action': 'ping'}

        headers = SimulatorCommand.get_headers(args)

        producer.publish(message, headers=headers)

        with consumer:
            try:
                while True:
                    connection.drain_events(timeout=10)
            except socket.timeout:
                pass

    @staticmethod
    def on_message(message):
        if 'state' in message.payload:
            sys.stdout.write('%s\n' % json.dumps(message.payload))
            sys.stdout.flush()


class SimulatorStartCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('start',
                                       help='Start a remote simulator')
        parser.add_argument('-p', '--parameters', metavar='JSON')
        parser.add_argument('-P', '--parameters-file', metavar='FILE')
        parser.add_argument('-m', '--model', metavar='JSON')
        parser.add_argument('-r', '--results', metavar='JSON')
        parser.add_argument('-w', '--when', metavar='JSON')
        parser.set_defaults(func=SimulatorStartCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas',
                                  type='headers',
                                  durable=True)

        producer = kombu.Producer(channel, exchange=exchange)

        message = {'action': 'start'}

        if args.parameters is not None:
            message['parameters'] = _get_parameters(args)

        try:
            if args.model is not None:
                message['model'] = json.loads(args.model)
            if args.results is not None:
                message['results'] = json.loads(args.results)
        except json.JSONDecodeError as e:
            LOGGER.error('Failed to parse parameters: %s at line %d column %d',
                         e.msg, e.lineno, e.colno)

        producer.publish(message, headers=SimulatorCommand.get_headers(args))


class SimulatorStopCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('stop',
                                       help='Stop a running remote simulator')
        parser.set_defaults(func=SimulatorStopCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas',
                                  type='headers',
                                  durable=True)

        producer = kombu.Producer(channel, exchange=exchange)

        message = {'action': 'stop'}

        producer.publish(message, headers=SimulatorCommand.get_headers(args))


class SimulatorPauseCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('pause',
                                       help='Pause a running simulator')
        parser.set_defaults(func=SimulatorPauseCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas',
                                  type='headers',
                                  durable=True)

        producer = kombu.Producer(channel, exchange=exchange)

        message = {'action': 'pause'}

        producer.publish(message, headers=SimulatorCommand.get_headers(args))


class SimulatorResumeCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('resume',
                                       help='Resume a paused remote simulator')
        parser.set_defaults(func=SimulatorResumeCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas',
                                  type='headers',
                                  durable=True)

        producer = kombu.Producer(channel, exchange=exchange)

        message = {'action': 'resume'}

        producer.publish(message, headers=SimulatorCommand.get_headers(args))


class SimulatorResetCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('reset',
                                       help='Reset a remote simulator from error state')  # noqa F501
        parser.set_defaults(func=SimulatorResetCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas', type='headers', durable=True)
        producer = kombu.Producer(channel, exchange=exchange)

        message = {'action': 'reset'}

        producer.publish(message,
                         headers=SimulatorCommand.get_headers(args))


class SimulatorCreateCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('create',
                                       help='Create a new simulator')  # noqa F501
        parser.add_argument('-p', '--parameters', metavar='JSON')
        parser.add_argument('-P', '--parameters-file', metavar='FILE')
        parser.set_defaults(func=SimulatorCreateCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas', type='headers', durable=True)
        producer = kombu.Producer(channel, exchange=exchange)

        message = {
            'action': 'create',
            'parameters': _get_parameters(args)
        }

        producer.publish(message,
                         headers=SimulatorCommand.get_headers(args))


class SimulatorDeleteCommand(Command):

    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('delete',
                                       help='Delete a simulator')  # noqa F501
        parser.add_argument('-p', '--parameters', metavar='JSON')
        parser.add_argument('-P', '--parameters-file', metavar='FILE')
        parser.set_defaults(func=SimulatorDeleteCommand.run)

    @staticmethod
    def run(connection, args):
        channel = connection.channel()

        exchange = kombu.Exchange('villas', type='headers', durable=True)
        producer = kombu.Producer(channel, exchange=exchange)

        message = {
            'action': 'delete',
            'parameters': _get_parameters(args)
        }

        producer.publish(message,
                         headers=SimulatorCommand.get_headers(args))
