#!/usr/bin/env python3
import sys
import asyncio
import asab
import logging

#

L = logging.getLogger(__file__)

#


class SampleApplication(asab.Application):


	async def initialize(self):
		self.PubSub.subscribe("Application.tick!", self.sample_pubsub_on_tick)

		#L.info("Adding a new module")
		from module_sample import Module
		self.add_module(Module)


	async def main(self):
		
		# Example of Service usage
		svc = self.get_service("service_sample")
		svc.hello()

		await asyncio.sleep(10)

		self.stop()


	def sample_pubsub_on_tick(self, message_type):
		L.info(message_type)

	def sample_pubsub_on_consume(self, message_type, arg1, arg2, arg3, kwsample):
		L.info("Message processed by a subscriber %s %d %d %d %d", message_type, arg1, arg2, arg3, kwsample)

	def sample_pubsub_add_subscriber(self):
		self.PubSub.subscribe("test_message", self.sample_pubsub_on_consume)
		L.info("Subscriber added.")

	def sample_pubsub_remove_subscriber(self):
		self.PubSub.unsubscribe("test_message", self.sample_pubsub_on_consume)
		L.info("Subscriber removed.")

	def sample_pubsub_publish(self):
		L.info("Message to be published.")
		self.PubSub.publish("test_message", 1, 2, 3, kwsample=1)

	def sample_pubsub_publish_to_unreg(self):
		"""
		This is sample message handled that is unregistered to PubSub
		"""
		L.info("Unregistered message to be published.")
		self.PubSub.publish("test_wrong_message")

	def sample_pubsub_publish_asynchonously(self):
		L.info("Message to be published asynchonously.")
		self.PubSub.publish("test_message", 3, 2, 1, kwsample=1, asynchronously=True)
		L.info("Publishing done.")

	def sample_metrics_add(self):
		L.info("Adding a metric.")
		self.Metrics.add("sample.metric", 10)

	def sample_metrics_set(self):
		L.info("Setting a metric.")
		self.Metrics.set("sample.metric", 90)

	def sample_metrics_pop(self):
		value = self.Metrics.pop("sample.metric")
		L.info("Popping a metric: {}.".format(value))

	def sample_metrics_keys(self):
		L.info("Reading metrics keys {}".format(self.Metrics.keys()))

###

if __name__ == '__main__':
	app = SampleApplication()

	# Example of PubSub mechanism
	app.sample_pubsub_add_subscriber()
	app.sample_pubsub_publish()
	app.sample_pubsub_remove_subscriber()
	app.sample_pubsub_publish()
	app.sample_pubsub_publish_to_unreg()

	app.sample_pubsub_add_subscriber()
	app.sample_pubsub_publish_asynchonously()

	# Example of Metric mechanism
	app.sample_metrics_set()
	app.sample_metrics_add()
	app.sample_metrics_pop()
	app.sample_metrics_keys()

	ret = app.run()
	sys.exit(ret)
