#!/usr/bin/env python3
import asab
import asyncio


class StatesDemonstrationApplication(asab.Application):

	def __init__(self, args=None):
		super().__init__(args)
		asyncio.ensure_future(self.async_init_task())
		# asyncio.create_task(self.async_init_task())

		print("*****\n1. Synchronous init takes place.")
		print("   Async tasks are being added to the loop, but are never awaited")

	async def initialize(self):
		self.PubSub.subscribe("Application.tick!", self.when_done)
		asyncio.ensure_future(self.async_initialize_task())

		print("*****\n3-5. Asynchronous initializatin takes place.")
		print("   app.initialize is run concurrently")
		print("   \"Application.init!\" is published")
		await asyncio.sleep(1)
		print("*****\n6-8. app.initialize awaited")

	async def async_init_task(self):
		print("*****\n3-5. Scheduled async tasks are run concurrently")
		await asyncio.sleep(2)
		print("*****\n6-8. All scheduled async tasks awaited")

	async def async_initialize_task(self):
		print("*****\n3-5. Even the ones scheuled in futures themselves.")
		await asyncio.sleep(3)
		print("*****\n6-8. Even the ones scheuled in futures themselves.")

	async def main(self):
		asyncio.ensure_future(self.async_main_task())

		print("*****\n7. Run time starts. app.main() is called")
		print("   then async tasks are being handled, until the application is stopped.")
		print("   \"Application.init!\" is published, application also starts ticking")


	async def async_main_task(self):
		print("*****\n8. Scheduled async tasks run concurrenlty")
		await asyncio.sleep(10)

	async def when_done(self, event_type):
		print("*****\n9. app.stop() is called by user code, or application is interupted in terminal")
		print("   Asab waits 3 seconds to let all scheduled async tasks finish and then exits.")
		print("   If some tasks are still pending throws warning.")
		self.stop()

	async def finalize(self):
		print("*****\n10. app.finilize is called, all modules and services are finalized.	")



if __name__ == '__main__':
	app = StatesDemonstrationApplication()
	print("*****\n2. Now application waits for run method to be called")
	app.run()
