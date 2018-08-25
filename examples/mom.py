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
		self.Broker = AMQPBroker(self, config={
			'url': 'amqp://testuser:test@rabbitmq1/playground',
		})

		# The timer will trigger a message publishing at every second
		self.PubSub.subscribe("Application.tick!", self.on_tick)

		# Subscribe and add the route
		self.Broker.subscribe("task.queue")
		self.Broker.add("example", self.handler)


	async def on_tick(self, event_type):
		await self.Broker.publish("Hello world!", target="example")


	async def handler(self, properties, body):
		print("Received:", body)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
