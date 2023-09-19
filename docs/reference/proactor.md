# Proactor Service

Proactor Service is useful for executing CPU bound operations, e.g., mathematical computations, data transformation, sorting or cryptographic algorithms, which would potentially block the main thread. Proactor service will execute these operations in a [ThreadPoolExecutor](https://www.geeksforgeeks.org/how-to-use-threadpoolexecutor-in-python3/).

!!! info "CPU bound operations"
	CPU bound are tasks where the speed or performance is primarily limited by the processing power of the CPU rather than by I/O or other resources. In a CPU-bound operation, the task spends most of its time performing calculations or processing data rather than waiting for external resources like disk or network to become available.

!!! example

	```python
	class MyApp(asab.Application):
		async def initialize(self):
			from asab.proactor import Module
				self.add_module(Module)
				self.ProactorService = self.App.get_service("asab.ProactorService")
		
		async def main(self):
			result = await self.ProactorService.execute(self.blocking_function)
	```

::: asab.proactor.service.ProactorService

