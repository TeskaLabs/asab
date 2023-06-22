Storage
=======

The ASAB's Storage Service supports data storage in-memory or in
dedicated document databases, including
[MongoDB](https://www.mongodb.com/) and
[ElasticSearch](https://www.elastic.co/).

Configuration
-------------

First, specify the storage type in the configuration. The options for
the storage type are:

-   `inmemory`: Collects data directly in memory
-   `mongodb`: Collects data using MongoDB database. Depends on
    [pymongo](https://pymongo.readthedocs.io/en/stable/) and
    [motor](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html)
    libraries.
-   `elasticsearch`: Collects data using ElasticSearch database.
    Depends on [aiohttp](https://docs.aiohttp.org/en/latest/) library.

Storage Service provides a unified interface for accessing and
manipulating collections across multiple database technologies.

``` {.ini}
[asab:storage]
type=mongodb
```

For accessing the storage, simply add
[asab.storage.Module]{.title-ref}` when initializing and register the
service.

``` {.python}
class MyApplication(asab.Application):

    async def initialize(self):

        self.add_module(asab.storage.Module)

    async def main(self):
        storage = self.get_service("asab.StorageService")
```
