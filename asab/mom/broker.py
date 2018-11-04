import abc
import logging
import asyncio
import asab

#

L = logging.getLogger(__name__)

#

class Broker(abc.ABC, asab.ConfigObject):

	def __init__(self, app, accept_replies:bool, task_service, config_section_name:str, config=None):
		if task_service == None:
			task_service = app.get_service("asab.MOMService")

		super().__init__(config_section_name=config_section_name, config=config)
		self.TaskService = task_service
		self.TaskService._register_broker(self)

		self.Loop = app.Loop
		self.Subscriptions = dict()
		self.Targets = {}
		self.AcceptReplies = accept_replies

		self.MainFuture = asyncio.ensure_future(self.main(), loop=self.Loop)


	async def finalize(self, app):
		self.MainFuture.cancel()


	def subscribe(self, subscription:str, **kwags):
		self.Subscriptions[subscription] = kwags
		asyncio.ensure_future(self.ensure_subscriptions(), loop=self.Loop)


	def add(self, target:str, handler):
		t = self.Targets.get(target)
		if t is None:
			self.Targets[target] = [handler]
		else:
			t.append(handler)


	async def dispatch(self, target, properties, body):
		tlist = self.Targets.get(target)
		if tlist is None:
			L.warn("Received a message for an unknown target '{}'".format(target))
			return

		for handler in tlist:
			reply = await handler(properties, body)
			if properties.reply_to is not None:
				#TODO: If reply_to is URL, then use HTTP to deliver reply
				await self.reply(reply,
					reply_to=properties.reply_to,
					correlation_id=properties.correlation_id,
				)
			elif reply is not None:
				L.warn("Discart the reply from target '{}'".format(target))



	async def main(self):
		pass


	async def ensure_subscriptions(self):
		pass


	async def publish(self, body, target:str='',
		content_type:str=None,
		content_encoding:str=None,
		correlation_id:str=None,
		reply_to:str=None,
		):
		pass


	async def reply(self, body,
		reply_to:str,
		content_type:str=None,
		content_encoding:str=None,
		correlation_id:str=None,
		):
		pass
