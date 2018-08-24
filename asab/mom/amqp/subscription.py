
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


