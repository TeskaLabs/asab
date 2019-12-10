#!/usr/bin/env python3
import concurrent.futures
import threading
import asyncio
import asab

'''
This example demonstrates the integration of ASAB event loop with ThreadPoolExecutor.

It is useful to offload long-running or blocking tasks from the main event loop into a dedicated thread.
It provides the seamless integration with the async world so that the caller can await the result of the worker thread.
Thanks to ThreadPoolExecutor, the worker threads are pre-created and managed in the pool.
'''


def task(n):
	print("Executing our Task")
	result = n
	i = 0
	for i in range(10):
		result = result + i
	print("I: {}".format(result))
	print("Task Executed {}".format(threading.current_thread()))
	return result


class MyApplication(asab.Application):

	asab.Config.add_defaults({
		'asab': {
			'workers': 3
		}
	})

	def __init__(self):
		super().__init__()

		self.Executor = concurrent.futures.ThreadPoolExecutor(
			max_workers=asab.Config.getint('asab', 'workers')
		)


	async def main(self):
		tasks = []
		for i in range(100):
			t = self.Loop.run_in_executor(self.Executor, task, i)
			tasks.append(t)

		results = await asyncio.gather(*tasks, loop=self.Loop)
		print("Result:", sum(results))

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
