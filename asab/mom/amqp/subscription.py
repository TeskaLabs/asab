import itertools

class QueueSubscriptionObject(object):

	def __init__(self, broker, queue_name, exchange:bool=False):
		self.Broker = broker
		self.QueueName = queue_name

		def on_channel_open(channel):
			channel.basic_qos(prefetch_count=int(self.Broker.Config['prefetch_count']), callback=on_qos_applied)

		def on_qos_applied(method):
			self.Channel.basic_consume(self.QueueName, on_consume_message)

		def on_consume_message(channel, method, properties, body):
			try:
				self.Broker.InboundQueue.put_nowait((channel, method, properties, body))
			except:
				channel.basic_nack(method.delivery_tag, requeue=True)

		self.Channel = self.Broker.Connection.channel(on_open_callback=on_channel_open)


class ExchangeSubscriptionObject(object):
	'''
	This class handles a subscription to a topic exchange.
	It creates a temporary exclusive queue that is bound to a specified exchange.

	Usage:
	Broker.subscribe("amq.topic", topic="*.orange.*")

	... or for multiple topics via subscription to an exchange
	
	Broker.subscribe("amq.topic", exchange=True, routing_key=["*.orange.*", "*.*.rabbit"])
	'''

	QueueNumberSeq = itertools.count(1)

	def __init__(self, broker, exchange_name:str, exchange:bool=True, routing_key:str=None):
		self.Broker = broker
		self.QueueName = "~T{}@".format(next(self.QueueNumberSeq))+broker.Origin
		self.ExchangeName = exchange_name
		if isinstance(routing_key, list):
			self.RoutingKey = routing_key
		else:
			self.RoutingKey = [routing_key]

		def on_channel_open(channel):
			channel.queue_declare(
				queue=self.QueueName,
				exclusive=True,
				auto_delete=True,
				callback=on_queue_declared,
			)
		
		def on_queue_declared(method):
			self.Channel.basic_qos(
				prefetch_count=int(self.Broker.Config['prefetch_count']),
				callback=on_qos_applied,
			)
			for rk in self.RoutingKey:
				self.Channel.queue_bind(
					queue=self.QueueName,
					exchange=self.ExchangeName,
					routing_key=rk
				)

		def on_qos_applied(method):
			self.Channel.basic_consume(
				self.QueueName,
				on_consume_message,
			)

		def on_consume_message(channel, method, properties, body):
			try:
				self.Broker.InboundQueue.put_nowait((channel, method, properties, body))
			except:
				channel.basic_nack(method.delivery_tag, requeue=True)

		self.Channel = self.Broker.Connection.channel(on_open_callback=on_channel_open)
