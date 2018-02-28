import logging
import asyncio
import os

from .pubsub import PubSub

class Application(object):

	def __init__(self):

		self.Loop = asyncio.get_event_loop()
		self.PubSub = PubSub(self)


	def run(self):
		self.Loop.run_forever()
		self.Loop.Close()

		return os.EX_OK
