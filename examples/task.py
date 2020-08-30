#!/usr/bin/env python3
import asab


class MyApplication(asab.Application):

	async def main(self):
		task_service = app.get_service("seacatpki.TaskService")

		# Schedule tasks to be executed
		# They will be executed in ~ 5 seconds
		task_service.schedule(
			self.task1(),
			self.task2(),
			self.task3(),
		)


	async def task1(self):
		print("Task1")

	async def task2(self):
		print("Task2")

	async def task3(self):
		print("Task3")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
