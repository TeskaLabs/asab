import asab


class MOMService(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.Brokers = set()
		self.Loop = app.Loop


	def _register_broker(self, broker):
		self.Brokers.add(broker)


	async def finalize(self, app):
		for b in self.Brokers:
			await b.finalize(app)
