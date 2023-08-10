# Modules and Services

ASAB applications contain several **Services**. Each Service is located in a separate **Module**.


## Registering Modules and Services

``` python
class MyApplication(asab.Application):
	async def initialize(self):
		from my_module import MyModule
		self.add_module(MyModule) #(1)!
		self.MyService = self.get_service("MyService") #(2)!
		...

# ...somewhere in the code

def custom_function():
	my_service = app.Services.get("MyService") #(3)!
	my_service.do_stuff()
```

1. The method [`add_module()`](/reference/application/reference/#asab.Application.add_module) initializes and adds a new module.
The `module_class` class will be instantiated during the method call.
2. The method [`get_service()`](reference/application/reference/#asab.Application.get_service) locates a service by its name and returns the [`asab.Service`](#asab.Service) object.
3. Modules that has been added to the application are stored in [`asab.Application.Modules`](/reference/application/reference/#asab.application.Application.Modules) list. Similarly, Services are stored in [`asab.Application.Services`](/reference/application/reference/#asab.Application.Services) dictionary.


## Built-in Services

Table of ASAB built-in Services and Modules:

| Service | Module | Features |
| --- | --- | --- |
| [`WebService`](/reference/web/web-server) | `asab.web` | Creating a web server. |
| [`StorageService`](/reference/storage/reference) | `asab.storage` | Storing the data in various databases. |
| [`LibraryService`](/reference/library/reference) | `asab.library` | Reading the data from various sources. |
| [`ZooKeeperService`](/reference/zookeeper/reference) | `asab.zookeeper` | Synchronizing data with Apache Zookeeper. |
| [`MetricService`](/reference/metrics/reference) | `asab.metric` | Analysis of the application state in a timescale manner.|
| [`AlertService`](/reference/alert/reference) | `asab.alert` | Integration of Alert Managers. |
| `TaskService`| `asab.task`| Execution of one-off background tasks. |
| `ProactorService` | `asab.proactor` | Running long-time activities asynchronously. |
| [`ApiService`](/reference/web/rest*_api_docs) | `asab.api` | Implementation of Swagger documentation. |


::: asab.Module

::: asab.Service
