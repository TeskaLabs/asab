#!/usr/bin/env python3
import asab


class TimerApplication(asab.Application):


	async def initialize(self):
		# The timer will trigger a message publishing at every second
		self.Timer = asab.Timer(self, self.on_tick, autorestart=True)
		self.Timer.start(1)


	async def on_tick(self):
		print("Think!")


if __name__ == '__main__':
	app = TimerApplication()
	app.run()
