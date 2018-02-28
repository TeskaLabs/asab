import logging
import asyncio
import os

from .pubsub import PubSub
from .config import Config

#

L = logging.getLogger(__file__)

#

class Application(object):

	def __init__(self):

		self.Loop = asyncio.get_event_loop()
		self.PubSub = PubSub(self)
		self.Config = Config(self)

	def run(self):
		L.info("Running...")
		self.Loop.run_forever()
		self.Loop.Close()

		return os.EX_OK
