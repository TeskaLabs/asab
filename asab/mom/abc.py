import abc
import logging
import asyncio
import asab

#

L = logging.getLogger(__name__)

#

class BrokerABC(abc.ABC, asab.ConfigObject):

	def __init__(self, app, task_service, config_section_name, config=None):
		if task_service == None:
			task_service = app.get_service("asab.MOMService")

		super().__init__(config_section_name=config_section_name, config=config)
		self.TaskService = task_service
		self.TaskService._register_broker(self)

		self.Loop = app.Loop
		self.Subscriptions = set()
		self.Targets = {}

		self.MainFuture = asyncio.ensure_future(self.main(), loop=self.Loop)


	async def finalize(self, app):
		self.MainFuture.cancel()


	def subscribe(self, queue_name):
		self.Subscriptions.add(queue_name)
		asyncio.ensure_future(self.ensure_subscriptions(), loop=self.Loop)


	def add(self, target, coro, reply_to=None):
		t = self.Targets.get(target)
		if t is None:
			self.Targets[target] = [(coro, reply_to)]
		else:
			t.append((coro, reply_to))


	async def dispatch(self, target, properties, body):
		tlist = self.Targets.get(target)
		if tlist is None:
			L.warn("Received a message for an unknown target '{}'".format(target))
			return

		for coro, reply_to in tlist:
			reply = await coro(properties, body)
			if reply_to is not None:
				await self.publish(reply,
					target=reply_to,
					correlation_id=properties.correlation_id
				)
			elif reply is not None:
				L.warn("Discart the reply from '{}'".format(target))



	async def main(self):
		pass


	async def ensure_subscriptions(self):
		pass


	async def publish(self, body, target=''):
		pass
