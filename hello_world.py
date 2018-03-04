#!/usr/bin/env python3
import asab

class MyApplication(asab.Application):
	async def main(self):
		print("Hello world!")
		self.stop()

if __name__ == '__main__':
	app = MyApplication()
	app.run()
