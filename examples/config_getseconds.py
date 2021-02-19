#!/usr/bin/env python3
import logging
import asyncio

import asab

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults({
	"sleep": {
		"for": "5.2s",
		"joke": "10d",
	}
})


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Two ways of obtaining seconds
		self.SleepFor = asab.Config["sleep"].getseconds("for")
		self.SleepJoke = asab.Config.getseconds("sleep", "joke")


	async def main(self):
		L.warning("Sleeping for '{}' seconds".format(self.SleepFor))

		await asyncio.sleep(self.SleepFor)

		L.warning("Sleeping done. You really do not want to sleep for another '{}' seconds.".format(self.SleepJoke))

		L.warning("Stopping the application.")
		self.stop()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
