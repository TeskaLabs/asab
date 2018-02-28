#!/usr/bin/env python3
import sys
import asab

###

class SampleApplication(asab.Application):
	def sample_pubsub_on_consume(self, arg1, arg2, arg3, kwsample):
		print("Event processed by a subscriber", arg1, arg2, arg3, kwsample)

	def sample_pubsub_add_subscriber(self):
		self.PubSub.subscribe("test_event", self.sample_pubsub_on_consume)
		print("Subscriber added.")

	def sample_pubsub_remove_subscriber(self):
		self.PubSub.unsubscribe("test_event", self.sample_pubsub_on_consume)
		print("Subscriber removed.")

	def sample_pubsub_publish(self):
		print("Event occurred.")
		self.PubSub.publish("test_event", 1, 2, 3, kwsample=1)

	def sample_pubsub_publish_to_unreg(self):
		"""
		This is sample event handled that is unregistered to PubSub
		"""
		print("Unregistered event occurred.")
		self.PubSub.publish("test_wrong_event")

###

if __name__ == '__main__':
	app = SampleApplication()

	# Example of PubSub mechanism
	app.sample_pubsub_add_subscriber()
	app.sample_pubsub_publish()
	app.sample_pubsub_remove_subscriber()
	app.sample_pubsub_publish()
	app.sample_pubsub_publish_to_unreg()

	ret = app.run()
	sys.exit(ret)
