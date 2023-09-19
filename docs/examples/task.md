---
author: mejroslav
commit: b14beb6f77c41c9efef5c1a365b31057f8b29cb4
date: 2023-09-19 11:52:35+02:00
title: Task

---

!!! example

	```python title='task.py' linenums="1"
	#!/usr/bin/env python3
	import asab
	import asyncio
	
	
	class MyApplication(asab.Application):
		async def main(self):
			print("Your tasks are scheduled. Meanwhile, take a deep breath and make yourself comfortable.")
			self.TaskService.schedule(
				self.task1(),
				self.task2(),
				self.task3(),  # throws Exception
			)
	
		async def task1(self):
			print("Task 1 started.")
			await asyncio.sleep(5.0)
			print("Task 1 is complete.")
	
		async def task2(self):
			print("Task 2 started.")
			await asyncio.sleep(5.0)
			print("Task 2 is complete.")
	
		async def task3(self):
			print("Task 3 started.")
			await asyncio.sleep(5.0)
			raise Exception("An exception occurred during Task 3.")
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
