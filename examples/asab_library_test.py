#!/usr/bin/env python3
import asab
import asab.api
import asab.library
import asyncio

L = asab.config.logging.getLogger(__name__)


class MyApplication(asab.Application):


	def __init__(self):
		super().__init__()

		# Loading the library service module
		self.add_module(asab.library.Module)

		libsvc = self.get_service("asab.LibraryService")
		async_response = []

		async def run_and_capture_result():
			r = await libsvc.read("schemas")
			async_response.append(r)

		loop = asyncio.get_event_loop()
		coroutine = run_and_capture_result()
		loop.run_until_complete(coroutine)
		L.warning("SCHEMA: {}".format(async_response[0]))

		# my_file = libsvc.read("schemas")
		# L.warning("SCHEMA: {}".format(my_file))

		# svc = asab.api.ApiService(self)
		# svc.initialize_zookeeper(zksvc.DefaultContainer)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
