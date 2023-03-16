.. currentmodule:: asab.storage

Storage
=======

ASAB provides a service for storing data. Data can be stored in memory or in dedicated document database. For now, it supports `MongoDB <https://www.mongodb.com/>`_ and `Elastic Search <https://www.elastic.co/>`_ databases.

Specification of the storage type
---------------------------------

In order to use `asab.storage`, first you have to specify the type of storage. You can add configurations in the config file 

.. code:: ini

    [asab:storage]
    type=mongodb

or you can set it manually in the ASAB app

.. code:: python

    import asab
    import asab.storage

    asab.Config.add_defaults(
        {
            'asab:storage': {
                'type': 'mongodb'
            }
        }
    )

The options for the storage type are:

- `inmemory`: collects data directly in memory
- `mongodb`: collects data using MongoDB database
- `elasticsearch`: collects data using Elastic Search database

Although these three databases are different, accessing the database and manipulation with collections is done by using the same methods.

For accessing the storage, simply add asab.storage.Module when initializing and register the service.

.. code:: python

    class MyApplication(asab.Application):

    async def initialize(self):

        self.add_module(asab.storage.Module)

    async def main(self):
        storage = self.get_service("asab.StorageService")


Manipulation with databases
---------------------------

Upsertor
~~~~~~~~

Upsertors are used for manipulations with databases. Upsertor is an object that works like a pointer to the specified database and optionally to object id.

.. code:: python

    u = storage.upsertor("test-collection")

This will create an upsertor object associated with the specified collection. It takes `collection` as an argument and can have two parameters `obj_id` and `version`, which are used for getting an existing object by its ID and version.

Inserting an object
~~~~~~~~~~~~~~~~~~~

For inserting an object to the collection, use the `set()` method.

.. code:: python

    u.set("key", "value")

To execute these procedures, simply run the `execute()` coroutine method, which commits the upsertor data to the storage and returns the ID of the object. Since it is a coroutine, it must be awaited.

.. code:: python

    object_id = await u.execute()

The `execute()` method has optional parameters `custom_data` and `event_type`, which are used for webhook requests.

.. code:: python

    object_id = await u.execute(custom_data= {"foo": "bar"},event_type="object_created")

Getting a single object
~~~~~~~~~~~~~~~~~~~~~~~

For getting a single object, use `get()` coroutine method that takes two arguments `collection` and `obj_id` and finds an object by its ID in collection.

.. code:: python

    obj = await storage.get(collection="test-collection", obj_id=object_id)

When the requested object is not found in the collection, the method raises ``KeyError``. Remember to handle this exception properly when using databases in your services and prevent them from crashing!

.. note::

    MongoDB storage service in addition provides a coroutine method `get_by()` which is used for accessing an object by finding its key-value pair. 

    .. code::python

        obj = await storage.get_by(database="test-collection", key="key", value="value")

Updating an object
~~~~~~~~~~~~~~~~~~

For updating an object, first obtain the upsertor specifying its `obj_id` and `version`.

.. code:: python

    u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v']

We strongly recommend to read version from the object such as above. That creates a soft lock on the record. It means that if the object is updated by other component in meanwhile, your upsertor will fail and you should retry the whole operation. The new objects should have a version set to 0, which is done by default.

After obtaining an upsertor, you can update the object via the `set()` coroutine.

.. code::python

    u.set("key", "new_value")
    object_id = await u.execute()


Deleting an object
~~~~~~~~~~~~~~~~~~

For deleting an object from database, use the `delete()` coroutine method which takes arguments `collection` and `obj_id`, deletes the object and returns its ID.

.. code:: python

    deleted_id = await u.delete("test-collection", object_id)



Storing data in memory
----------------------

If the option `inmemory` is set, ASAB will store data in its own memory. In particular, `asab.StorageService` is initialized with an attribute `InMemoryCollections` which is a dictionary where all the collections are stored in.

.. note::

    You can go through all the databases directly by accessing `InMemoryCollections` attribute, although we do not recommend that.

    .. code:: python

        import pprint

        storage = self.get_service("asab.StorageService")
        pprint.pprint(storage.InMemoryCollections, indent=2)


Storing data in MongoDB
-----------------------

If the option `mongodb` is set, ASAB will store data in MongoDB database.

ASAB uses `motor library <https://pypi.org/project/motor/>`_ which provides non-blocking MongoDB driver for `asyncio`.

Mongo Storage class provides in addition a method `database()` for accessing database directly. It takes `collection` as the argument and returns `motor.motor_asyncio.AsyncIOMotorCollection` object, which can be used for calling MongoDB directives. The full list of methods suitable for this object is described in `official motor documentation <https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html>`_


Storing data in Elastic Search
------------------------------

TODO


Encryption and decryption
-------------------------

TODO


Object ID
---------

TODO (how ID's are generated via `generateid()` method)