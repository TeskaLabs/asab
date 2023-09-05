#!/usr/bin/env python3
import asab
import time


class MyApplication(asab.Application):

	async def main(self):

		print("Your tasks are scheduled. Meanwhile, give a deep breath and make yourself comfortable.")

		# Every task takes 3 seconds to finish.
		self.TaskService.schedule(
			self.task1(),
			self.task2(),
			self.task3(),  # throws Exception
			self.task4(),
		)


	async def task1(self):
		print("Task 1 started.")
		time.sleep(3.0)
		print("Task 1 is complete.")

	async def task2(self):
		print("Task 2 started.")
		time.sleep(3.0)
		print("Task 2 is complete.")

	async def task3(self):
		print("Now, watch what happens if exception during Task occurs:")
		print("Task 3 started.")
		time.sleep(3.0)
		raise Exception("An exception occurred during Task 3.")

	async def task4(self):
			print("Task 4 started.")
			time.sleep(3.0)
			print("Task 4 is complete.")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
