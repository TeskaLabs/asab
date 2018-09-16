import itertools

class SubscriptionObject(object):

	def __init__(self, broker, queue_name):
		self.Broker = broker
		self.QueueName = queue_name

		def on_channel_open(channel):
			channel.basic_qos(on_qos_applied, prefetch_count=int(self.Broker.Config['prefetch_count']))

		def on_qos_applied(method):
			self.Channel.basic_consume(on_consume_message, self.QueueName)

		def on_consume_message(channel, method, properties, body):
			try:
				self.Broker.InboundQueue.put_nowait((channel, method, properties, body))
			except:
				channel.basic_nack(method.delivery_tag, requeue=True)

		self.Channel = self.Broker.Connection.channel(on_open_callback=on_channel_open)


class TopicSubscriptionObject(object):
	'''
	This class handles a subscription to a topic exchange.
	It creates a temporary exclusive queue that is bound to a specified exchange.

	Usage:
	Broker.subscribe("amq.topic", topic="*.orange.*")

	... or for multiple topics
	
	Broker.subscribe("amq.topic", topic=["*.orange.*", "*.*.rabbit"])
	'''

	QueueNumberSeq = itertools.count(1)

	def __init__(self, broker, exchange_name, topic):
		self.Broker = broker
		self.QueueName = "~T{}@".format(next(self.QueueNumberSeq))+broker.Origin
		self.ExchangeName = exchange_name
		if isinstance(topic, list):
			self.Topic = topic
		else:
			self.Topic = [topic]

		def on_channel_open(channel):
			channel.queue_declare(
				callback=on_queue_declared,
				queue=self.QueueName,
				exclusive=True,
				auto_delete=True,
			)
		
		def on_queue_declared(method):
			self.Channel.basic_qos(
				on_qos_applied,
				prefetch_count=int(self.Broker.Config['prefetch_count']),
			)
			for topic in self.Topic:
				self.Channel.queue_bind(
					None,
					queue=self.QueueName,
					exchange=self.ExchangeName,
					routing_key=topic,
					nowait=True, # We are not interested in the result
				)

		def on_qos_applied(method):
			self.Channel.basic_consume(
				on_consume_message,
				self.QueueName,
			)

		def on_consume_message(channel, method, properties, body):
			try:
				self.Broker.InboundQueue.put_nowait((channel, method, properties, body))
			except:
				channel.basic_nack(method.delivery_tag, requeue=True)

		self.Channel = self.Broker.Connection.channel(on_open_callback=on_channel_open)
