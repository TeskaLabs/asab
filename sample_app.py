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


	def sample_pubsub_on_tick(self, event_name):
		L.info("Application tick!")

	def sample_pubsub_on_consume(self, event_name, arg1, arg2, arg3, kwsample):
		L.info("Event processed by a subscriber %s %d %d %d %d", event_name, arg1, arg2, arg3, kwsample)

	def sample_pubsub_add_subscriber(self):
		self.PubSub.subscribe("test_event", self.sample_pubsub_on_consume)
		L.info("Subscriber added.")

	def sample_pubsub_remove_subscriber(self):
		self.PubSub.unsubscribe("test_event", self.sample_pubsub_on_consume)
		L.info("Subscriber removed.")

	def sample_pubsub_publish(self):
		L.info("Event to be published.")
		self.PubSub.publish("test_event", 1, 2, 3, kwsample=1)

	def sample_pubsub_publish_to_unreg(self):
		"""
		This is sample event handled that is unregistered to PubSub
		"""
		L.info("Unregistered event to be published.")
		self.PubSub.publish("test_wrong_event")

	def sample_pubsub_publish_async(self):
		L.info("Event to be published asynchonously.")
		self.PubSub.publish_async("test_event", 1, 2, 3, kwsample=1)
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
	app.sample_pubsub_publish_async()

	# Example of Metric mechanism
	app.sample_metrics_set()
	app.sample_metrics_add()
	app.sample_metrics_pop()
	app.sample_metrics_keys()

	ret = app.run()
	sys.exit(ret)
