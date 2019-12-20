import abc
import logging
import asyncio
import asab

#

L = logging.getLogger(__name__)

#


class Broker(abc.ABC, asab.ConfigObject):
	"""
		Broker is implementation of object request broker (ORB) within the Message-oriented middleware concept.

		Broker allows to register callbacks for "task" and "reply" procedures, via "add" method.
		Tasks and replies are then distributed to the registered callbacks.

			self.Broker.add("task", self.task_handler)
			self.Broker.add("reply", self.reply_handler)

		In order to connect broker with the middleware (such as RabbitMQ, see AMQPBroker in the "amqp" submodule),
		it is needed that the broker is subscribed to task and reply queues in the middleware, via "subscribe" method.

			self.Broker.subscribe("task.queue")

		The method "publish" the serve to publish a task to the middleware.

			await self.Broker.publish("Hello world!", target="task")

		The brokers from different applications can be connected to the same middleware,
		where one application may publish tasks, while others process them and publish replies.
	"""


	def __init__(self, app, accept_replies: bool, task_service, config_section_name: str, config=None):
		if task_service is None:
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


	def subscribe(self, subscription: str, **kwags):
		self.Subscriptions[subscription] = kwags
		asyncio.ensure_future(self.ensure_subscriptions(), loop=self.Loop)


	def add(self, target: str, handler):
		t = self.Targets.get(target)
		if t is None:
			self.Targets[target] = [handler]
		else:
			t.append(handler)


	async def dispatch(self, target, properties, body):
		tlist = self.Targets.get(target)
		if tlist is None:
			L.warning("Received a message for an unknown target '{}'".format(target))
			return

		for handler in tlist:
			reply = await handler(properties, body)
			if properties.reply_to is not None:
				# TODO: If reply_to is URL, then use HTTP to deliver reply
				await self.reply(
					reply,
					reply_to=properties.reply_to,
					correlation_id=properties.correlation_id,
				)
			elif reply is not None:
				L.warning("Discart the reply from target '{}'".format(target))



	async def main(self):
		pass


	async def ensure_subscriptions(self):
		pass


	async def publish(
		self,
		body,
		target: str = '',
		content_type: str = None,
		content_encoding: str = None,
		correlation_id: str = None,
		reply_to: str = None,
	):
		pass


	async def reply(
		self,
		body,
		reply_to: str,
		content_type: str = None,
		content_encoding: str = None,
		correlation_id: str = None,
	):
		pass
