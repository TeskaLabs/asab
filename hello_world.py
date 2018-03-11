#!/usr/bin/env python3
import asab
import logging

L = logging.getLogger(__name__)

class MyApplication(asab.Application):
	async def main(self):
		print("Hello world! And love to Nikol!")
		L.debug("DEBUG")
		L.info("INFO")
		L.warning("WARNING")
		L.error("ERROR")
		L.fatal("FATAL")
		self.stop()

if __name__ == '__main__':
	app = MyApplication()
	app.run()
