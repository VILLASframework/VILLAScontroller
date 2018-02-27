from .. import command

import kombu
import socket
import json

class SimulatorCommand(command.Command):

	@staticmethod
	def run(connection, args):
		pass

	def add_parser(subparsers):
		parser = subparsers.add_parser('simulator', help = 'Send control command to simulator')

		filt = parser.add_argument_group('Filter simulators')
		filt.add_argument('-r', '--realm')
		filt.add_argument('-c', '--category')
		filt.add_argument('-t', '--type')
		filt.add_argument('-u', '--uuid')

		sim_subparsers = parser.add_subparsers(
			title = 'action',
			metavar = 'ACTION',
			help = 'Available simulator commands'
		)
		sim_subparsers.required = True
		sim_subparsers.dest = 'command'

		SimulatorStartCommand.add_parser(sim_subparsers)
		SimulatorStopCommand.add_parser(sim_subparsers)
		SimulatorPauseCommand.add_parser(sim_subparsers)
		SimulatorResumeCommand.add_parser(sim_subparsers)
		SimulatorPingCommand.add_parser(sim_subparsers)

	@staticmethod
	def get_headers(args):
		headers = {}

		if args.realm:
			headers['realm'] = args.realm

		if args.uuid:
			headers['uuid'] = args.uuid

		if args.category:
			headers['category'] = args.category

		if args.type:
			headers['type'] = args.type

		return headers

class SimulatorPingCommand(command.Command):

	@staticmethod
	def add_parser(subparsers):
		parser = subparsers.add_parser('ping', help = 'Ping a remote simulator')
		parser.set_defaults(func = SimulatorPingCommand.run)

	@staticmethod
	def run(connection, args):
		channel = connection.channel()

		exchange = kombu.Exchange('villas',
			type = 'headers',
			durable = True
		)

		producer = kombu.Producer(channel,
			exchange = exchange
		)

		consumer = kombu.Consumer(channel,
			queues = kombu.Queue(
				exchange = exchange,
				durable = False
			),
			on_message = SimulatorPingCommand.on_message
		)

		message = {
			'action' : 'ping'
		}

		headers = SimulatorCommand.get_headers(args)

		producer.publish(message,
			headers = headers
		)

		with consumer:
			try:
				while True:
					connection.drain_events(timeout = 1)
			except socket.timeout:
				pass

	@staticmethod
	def on_message(message):
		if 'state' in message.payload:
			sys.stdout.write("%s\n" % json.dumps(message.payload))
			sys.stdout.flush()

class SimulatorStartCommand(command.Command):

	@staticmethod
	def add_parser(subparsers):
		parser = subparsers.add_parser('start', help = 'Start a remote simulator')
		parser.set_defaults(func = SimulatorStartCommand.run)

	@staticmethod
	def run(connection, args):
		channel = connection.channel()

		exchange = kombu.Exchange('villas',
			type = 'headers',
			durable = True
		)

		producer = kombu.Producer(channel,
			exchange = exchange
		)

		message = {
			'action' : 'start'
		}

		producer.publish(message,
			headers = SimulatorCommand.get_headers(args)
		)

class SimulatorStopCommand(command.Command):

	@staticmethod
	def add_parser(subparsers):
		parser = subparsers.add_parser('stop', help = 'Stop a running remote simulator')
		parser.set_defaults(func = SimulatorStopCommand.run)

	@staticmethod
	def run(connection, args):
		channel = connection.channel()

		exchange = kombu.Exchange('villas',
			type = 'headers',
			durable = True
		)

		producer = kombu.Producer(channel,
			exchange = exchange
		)

		message = {
			'action' : 'stop'
		}

		producer.publish(message,
			headers = SimulatorCommand.get_headers(args)
		)

class SimulatorPauseCommand(command.Command):

	@staticmethod
	def add_parser(subparsers):
		parser = subparsers.add_parser('pause', help = 'Pause a running simulator')
		parser.set_defaults(func = SimulatorPauseCommand.run)

	@staticmethod
	def run(connection, args):
		channel = connection.channel()

		exchange = kombu.Exchange('villas',
			type = 'headers',
			durable = True
		)

		producer = kombu.Producer(channel,
			exchange = exchange
		)

		message = {
			'action' : 'pause'
		}

		producer.publish(message,
			headers = SimulatorCommand.get_headers(args)
		)

class SimulatorResumeCommand(command.Command):

	@staticmethod
	def add_parser(subparsers):
		parser = subparsers.add_parser('resume', help = 'Resume a paused remote simulator')
		parser.set_defaults(func = SimulatorResumeCommand.run)

	@staticmethod
	def run(connection, args):
		channel = connection.channel()

		exchange = kombu.Exchange('villas',
			type = 'headers',
			durable = True
		)

		producer = kombu.Producer(channel,
			exchange = exchange
		)

		message = {
			'action' : 'resume'
		}

		producer.publish(message,
			headers = SimulatorCommand.get_headers(args)
		)
