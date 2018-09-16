#!/usr/bin/env python3
import asab


class MyApplication(asab.Application):

	'''
	Run by:
	$ PYTHONPATH=.. ./mom.py

	RabbitMQ virtual host 'playground' setup:
	Exchange 'amqp.fanout' => queue 'task.queue'
	'''

	async def initialize(self):
		from asab.mom import Module
		self.add_module(Module)

		from asab.mom.amqp import AMQPBroker
		self.Broker = AMQPBroker(self, accept_replies=True, config={
			'url': 'amqp://guest:guest@localhost/',
		})

		# The timer will trigger a message publishing at every second
		self.PubSub.subscribe("Application.tick!", self.on_tick)

		# Add the route	
		self.Broker.add("task", self.task_handler)
		self.Broker.add("reply", self.reply_handler)


	async def main(self):
		# Subscribe and start working
		self.Broker.subscribe("task.queue")

		# This is a topic subscription
		# See https://www.rabbitmq.com/tutorials/tutorial-five-python.html for more details
		self.Broker.subscribe("amq.topic", exchange=True, routing_key=["*.orange.*", "*.*.rabbit"])


	async def on_tick(self, event_type):
		await self.Broker.publish("Hello world!", target="task")


	async def task_handler(self, properties, body):
		print("Received:", body)
		return "Reply!"


	async def reply_handler(self, properties, body):
		print("Reply:", body)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
