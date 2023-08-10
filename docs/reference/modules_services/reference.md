# Modules and Services

ASAB applications contain several **Services**. Each Service is located in a separate **Module**.


## Registering Modules and Services

The method [`asab.Application.add_module()`](/reference/application/reference/#asab.Application.add_module) initializes and adds a new module.
The `module_class` class will be instantiated during the method call.
Modules that has been added to the application are stored in [`asab.Application.Modules`](/reference/application/reference/#asab.application.Application.Modules) list.

``` python
class MyApplication(asab.Application):
	async def initialize(self):
		from my_module import MyModule
		self.add_module(MyModule)
```

The method [`asab.Application.add_service()`](#asab.Application.add_service) locates a service by its service name
in a registry [`Services`](/reference/application/reference/#asab.Application.Services) and returns the [`asab.Service`](#asab.Service) object.

``` python
svc = app.get_service("service_sample")
svc.hello()
```

## Built-in Services

Table of ASAB built-in Services and Modules:

| Service | Module | Features |
| --- | --- | --- |
| `WebService` | `asab.web` | Creating a web server. |
| `StorageService` | `asab.storage` | Storing the data in various databases. |
| [`LibraryService`](/reference/library/reference) | `asab.library` | Reading the data from various sources. |
| `ZooKeeperService` | `asab.zookeeper` | Synchronizing data with Apache Zookeeper. |
| [`MetricService`](/reference/metrics/service/) | `asab.metric` | Analysis of the application state in a timescale manner.|
| `AlertService`| `asab.alert` | Integration of Alert Managers. |
| `TaskService`| `asab.task`| Execution of one-off background tasks. |
| `ProactorService` | `asab.proactor` | Running long-time activities asynchronously. |
| `ApiService`| `asab.api` | Implementation of Swagger documentation. |


::: asab.Module

::: asab.Service
