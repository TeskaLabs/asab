import logging
import asyncio
import os

from .config import Config
from .abc.singleton import Singleton
from .pubsub import PubSub
from .metrics import Metrics

#

L = logging.getLogger(__file__)

#

class Application(metaclass=Singleton):


	def __init__(self):

		# Load configuration
		self.Config = Config
		self.Config.load()

		self.Loop = asyncio.get_event_loop()
		self.PubSub = PubSub(self)
		self.Metrics = Metrics(self)


	def run(self):
		L.info("Running...")
		self.Loop.run_forever()
		self.Loop.Close()

		return os.EX_OK
