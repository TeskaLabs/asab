#!/usr/bin/env python3
import asab
import asyncio


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Make sure that the proactor service exists
		from asab.proactor import Module
		self.add_module(Module)
		self.ProactorService = self.get_service("asab.ProactorService")

		self.PubSub.subscribe("Application.tick!", self.on_tick)

		self.Count = 0

	def on_tick(self, event_name):
		print("Count", self.Count)

	async def main(self):
		i = 0
		while True:
			self.ProactorService.schedule(self.task1)
			self.ProactorService.schedule(self.task2)
			self.ProactorService.schedule(self.task3)

			i += 1
			if i > 1000:
				await asyncio.sleep(0.001)
				i = 0

	def task1(self):
		self.Count += 1

	def task2(self):
		self.Count += 3

	def task3(self):
		self.Count += 5


if __name__ == '__main__':
	app = MyApplication()
	app.run()
