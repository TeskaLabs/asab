# Task Service

Task service is for managed execution of fire-and-forget, one-off, background tasks.

**Task** in this context is represented either by a coroutine, `asyncio.Future` or `asyncio.Task` instance and it is executed in the main event loop.

The result of the task is collected (and discarded) automatically.
When the task raises Exception, it will be printed to the log.

!!! info "I/O bound operations"

	`TaskService` is handy for dealing with so called "I/O bound operations". These operations refer to tasks that spend more time waiting for input/output operations to complete than they do performing actual computations, e.g., reading or writing large files from/to a disk, making API calls, fetching data from a remote database. The speed of these operations is determined by the speed of the I/O subsystems, such as disk drivers, network interfaces, etc.

!!! example "Usage of Task Service"

	The `TaskService` is implemented in every ASAB application and accessible as `asab.Application.TaskService`.

	```python
	class MyApp(asab.Application):
		async def main(self):
			asab.Application.TaskService.schedule(
				self.task1(),
				self.task2(),
				self.task3(),
			)
	```


## Reference

::: asab.task.TaskService