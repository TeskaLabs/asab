#!/usr/bin/env python3
import logging
import asab

L = logging.getLogger(__name__)


class MyApplication(asab.Application):
	async def main(self):
		L.warning("Hello world!")
		self.stop()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
