#!/usr/bin/env python3
import logging
import asab

#

L = logging.getLogger(__name__)

#


class MyApplication(asab.Application):
	"""
	python3 logging-file.py -c ./data/logging-file.conf
	"""

	async def main(self):
		L.warning("Sample log WARNING!")
		L.error("Sample log ERROR!")
		self.stop()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
