import asab


class MOMService(asab.Service):
	"""
	MOMService implements message-oriented middleware:
	https://en.wikipedia.org/wiki/Message-oriented_middleware

	MOMService register brokers to post tasks to the task queue
	or process tasks and post them to the reply queue.
	"""


	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Brokers = set()


	def _register_broker(self, broker):
		self.Brokers.add(broker)


	async def finalize(self, app):
		for b in self.Brokers:
			await b.finalize(app)
