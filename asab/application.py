import logging
import asyncio
import os

class Application(object):

	def __init__(self):

		self.Loop = asyncio.get_event_loop()


	def run(self):
		self.Loop.run_forever()
		self.Loop.Close()

		return os.EX_OK
