#!/usr/bin/env python3
import sys
import asab

###

class SampleApplication(asab.Application):
	def sample_pubsub_on_consume(self, event_name, arg1, arg2, arg3, kwsample):
		print("Event processed by a subscriber", event_name, arg1, arg2, arg3, kwsample)

	def sample_pubsub_add_subscriber(self):
		self.PubSub.subscribe("test_event", self.sample_pubsub_on_consume)
		print("Subscriber added.")

	def sample_pubsub_remove_subscriber(self):
		self.PubSub.unsubscribe("test_event", self.sample_pubsub_on_consume)
		print("Subscriber removed.")

	def sample_pubsub_publish(self):
		print("Event to be published.")
		self.PubSub.publish("test_event", 1, 2, 3, kwsample=1)

	def sample_pubsub_publish_to_unreg(self):
		"""
		This is sample event handled that is unregistered to PubSub
		"""
		print("Unregistered event to be published.")
		self.PubSub.publish("test_wrong_event")

	def sample_pubsub_publish_async(self):
		print("Event to be published asynchonously.")
		self.PubSub.publish_async("test_event", 1, 2, 3, kwsample=1)
		print("Publishing done.")

	def sample_metrics_add(self):
		print("Adding a metric.")
		self.Metrics.add("sample.metric", 10)

	def sample_metrics_set(self):
		print("Setting a metric.")
		self.Metrics.set("sample.metric", 90)

	def sample_metrics_pop(self):
		value = self.Metrics.pop("sample.metric")
		print("Popping a metric: {}.".format(value))

	def sample_metrics_keys(self):
		print("Reading metrics keys", self.Metrics.keys())

	def sample_module_add(self):
		print("Adding a new module")
		from module_sample import Module
		self.add_module(Module)
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

	# Example of Module mechanism
	# The module also registers service_sample
	app.sample_module_add()

	# Example of Service usage
	svc = app.get_service("service_sample")
	svc.hello()

	ret = app.run()
	sys.exit(ret)
