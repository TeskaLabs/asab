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

	ret = app.run()
	sys.exit(ret)
