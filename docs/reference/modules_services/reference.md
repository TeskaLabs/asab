# Modules and Services

ASAB applications contain several **Services**. Each Service is located in a separate **Module**.

## Built-in Services and Modules:

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
