---
author: eliska
commit: d83dcedb619098678100883d1faa15ad2b08e878
date: 2022-02-09 10:16:42+01:00
title: Task

---

!!! example

	```python title='task.py' linenums="1"
	#!/usr/bin/env python3
	import asab
	
	
	class MyApplication(asab.Application):
	
		async def main(self):
			task_service = app.get_service("asab.TaskService")
	
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
	
	```
