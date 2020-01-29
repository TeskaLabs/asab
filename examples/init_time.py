#!/usr/bin/env python3
import asab


class InitTimeExampleApplication(asab.Application):

	def __init__(self, args=None):
		super().__init__(args)
		print("*****\n1. Synchronous init takes place.")
		print("\n   Async tasks are being added to the loop, but are never awaited")

	async def initialize(self):
		self.PubSub.subscribe("Application.tick/10!", self.when_done)
		print("*****\n3. Asynchronous initializatin takes place.")
		print("   app.initialize is called and whole async queue is awaited")
		print("   \"Application.init!\" is published")

	async def main(self):
		print("*****\n4. Run time starts. app.main() is called")
		print("   then async tasks are being handled, until the application is stopped.")
		print("   \"Application.init!\" is published, application also starts ticking")


	async def when_done(self, event_type):
		print("*****\n5. app.stop() is called by user code, or application is interupted in terminal")
		print("   Asab tries to hadle all scheduled async tasks and then exits.")
		self.stop()


if __name__ == '__main__':
	app = InitTimeExampleApplication()
	print("*****\n2. Now application waits for run method to be called")
	app.run()
