.. currentmodule:: asab.storage

Storage
=======

The ASAB's Storage Service supports data storage in-memory or in dedicated document databases, including  `MongoDB <https://www.mongodb.com/>`_ and `ElasticSearch <https://www.elastic.co/>`_.

Storage Types
-------------

First, specify the storage type in the configuration. The options for the storage type are:

- `inmemory`: Collects data directly in memory
- `mongodb`: Collects data using MongoDB database. Depends on `pymongo <https://pymongo.readthedocs.io/en/stable/>`_ and `motor <https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html>`_ libraries.
- `elasticsearch`: Collects data using ElasticSearch database. Depends on `aiohttp <https://docs.aiohttp.org/en/latest/>`_ library.

Storage Service provides a unified interface for accessing and manipulating collections across multiple database technologies. 

.. code:: ini

    [asab:storage]
    type=mongodb

For accessing the storage, simply add `asab.storage.Module`` when initializing and register the service.

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

The :func:`upsertor()` method creates an upsertor object associated with the specified collection. It takes `collection` as an argument and can have two parameters `obj_id` and `version`, which are used for getting an existing object by its ID and version.

Inserting an object
~~~~~~~~~~~~~~~~~~~

For inserting an object to the collection, use the `set()` method.

.. code:: python

    u.set("key", "value")

To execute these procedures, simply run the :func:`execute()` coroutine method, which commits the upsertor data to the storage and returns the ID of the object. Since it is a coroutine, it must be awaited.

.. code:: python

    object_id = await u.execute()

The `execute()` method has optional parameters `custom_data` and `event_type`, which are used for webhook requests.

.. code:: python

    object_id = await u.execute(custom_data= {"foo": "bar"},event_type="object_created")

Getting a single object
~~~~~~~~~~~~~~~~~~~~~~~

For getting a single object, use :func:`get()` coroutine method that takes two arguments `collection` and `obj_id` and finds an object by its ID in collection.

.. code:: python

    obj = await storage.get(collection="test-collection", obj_id=object_id)

When the requested object is not found in the collection, the method raises ``KeyError``. Remember to handle this exception properly when using databases in your services and prevent them from crashing!

.. note::

    MongoDB storage service in addition provides a coroutine method :func:`get_by()` which is used for accessing an object by finding its key-value pair. 

    .. code::python

        obj = await storage.get_by(database="test-collection", key="key", value="value")

Updating an object
~~~~~~~~~~~~~~~~~~

For updating an object, first obtain the upsertor specifying its `obj_id` and `version`.

.. code:: python

    u = storage.upsertor("test-collection", obj_id=object_id, version=obj['_v']

We strongly recommend to read the version from the object such as above. That creates a soft lock on the record. It means that if the object is updated by other component in meanwhile, your upsertor will fail and you should retry the whole operation. The new objects should have a version set to 0, which is done by default.

After obtaining an upsertor, you can update the object via the :func:`set()` coroutine.

.. code::python

    u.set("key", "new_value")
    object_id = await u.execute()


Deleting an object
~~~~~~~~~~~~~~~~~~

For deleting an object from database, use the :func:`delete()` coroutine method which takes arguments `collection` and `obj_id`, deletes the object and returns its ID.

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

You can specify the database name and URL for MongoDB in config file (the following example is the default configuration):

.. code:: ini

    [asab:storage]
    type=mongodb
    mongodb_uri=mongodb://localhost:27017
    mongodb_database=asabdb



.. py:method:: StorageService.get_by(collection: str, key: str, value, decrypt = None) -> dict


.. py:method:: StorageService.collection(collection: str) -> motor.motor_asyncio.AsyncIOMotorCollection

Mongo Storage class provides in addition a method :func:`collection()` for accessing database directly. It takes `collection` as the argument and returns `motor.motor_asyncio.AsyncIOMotorCollection` object, which can be used for calling MongoDB directives. 

Example of the use:

.. code:: python

    collection = await storage.collection("test-collection")
    cursor = collection.find({})
    while await cursor.fetch_next:
        data = cursor.next_object()
        pprint.pprint(data)

The full list of methods suitable for this object is described in the `official documentation <https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html>`_.



Storing data in ElasticSearch
------------------------------

When using ElasticSearch, add configurations for URL, username and password.

.. code:: ini

    [asab:storage]
    type=elasticsearch
    elasticsearch_url=http://localhost:9200/
    elasticsearch_username=JohnDoe
    elasticsearch_password=lorem_ipsum_dolor?sit_amet!2023

You can also specify `refreshing parameter <https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-refresh.html#docs-refresh>`_ and scroll timeout for `ElasticSearch Scroll API <https://www.elastic.co/guide/en/elasticsearch//reference/current/scroll-api.html>`_.

.. code:: ini

    [asab:storage]
    refresh=true
    scroll_timeout=1m



Encryption and decryption
-------------------------

The :func:`set()` method has an optional parameter `encrypt` which provides an encryption option for data that you want to store in the database. 



Algorithm for encrypting
~~~~~~~~~~~~~~~~~~~~~~~~

For encrypting data, we use the certified symmetric AES-CBC algorithm. In fact, the abstract base class :class:`StorageServiceABC` provides two methods :func:`aes_encrypt()` and :func:`aes_decrypt()` that are called automatically in :func:`set()` and :func:`get()` methods when the parameter `encrypt` or `decrypt` is specified.

.. note::

    AES-CBC is a mode of operation for the Advanced Encryption Standard (AES) algorithm that provides confidentiality and integrity for data. In AES-CBC, the plaintext is divided into blocks of fixed size (usually 128 bits), and each block is encrypted using the AES algorithm with a secret key.

    CBC stands for "Cipher Block Chaining" and it is a technique that adds an extra step to the encryption process to ensure that each ciphertext block depends on the previous one. This means that any modification to the ciphertext will produce a completely different plaintext after decryption.

    The algorithm is a symmetric cipher, which is suitable for encrypting large amounts of data. It requires much less computation power than asymmetric ciphers and is much more useful for bulk encrypting large amounts of data.



Reference
---------

In-memory storage
~~~~~~~~~~~~~~~~~

.. currentmodule:: asab.storage.inmemory

.. autoclass:: StorageService
    :show-inheritance:

    .. automethod:: upsertor

    .. automethod:: get

    .. automethod:: get_by
    
    .. automethod:: delete

.. autoclass:: InMemoryUpsertor

    .. automethod:: execute


MongoDB Storage
~~~~~~~~~~~~~~~

TODO: make changes in MongoDB storage.

.. currentmodule:: asab.storage.mongodb

.. autoclass:: StorageService
    :show-inheritance:

    .. automethod:: upsertor

    .. automethod:: get

    .. automethod:: get_by

    .. automethod:: collection

    .. automethod:: delete

.. autoclass:: MongoDBUpsertor

    .. automethod:: generate_id

ElasticSearch Storage
~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: asab.storage.elasticsearch

.. autoclass:: StorageService
    :show-inheritance:

    .. automethod:: upsertor

    .. automethod:: session

    .. automethod:: finalize

    .. automethod:: get

    .. automethod:: get_by

    .. automethod:: delete

    .. automethod:: mapping

    .. automethod:: get_index_template

    .. automethod:: put_index_template

    .. automethod:: reindex

    .. automethod:: scroll

    .. automethod:: list

    .. automethod:: count

    .. automethod:: indices

    .. automethod:: empty_index