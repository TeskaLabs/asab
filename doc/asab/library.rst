.. _library-ref:

Library
=======

.. py:currentmodule:: asab.library

The ASAB Library (`asab.library`) is a concept of the shared data content across microservices in the cluster.
The `asab.library` provides a read-only interface for listing and reading this content.
The library can also notify the ASAB microservice about changes, eg. for automated update/reload.

There is a companion microservice `asab-library` that can be used for management and editation of the library content.
The `asab.library` can however operate without `asab-library` microservice.


Library structure
-----------------

The library content is organized in simplified filesystem manner, with directories and files.

Example:

.. code:: 

 + /folder1/
   - /folder1/item1.yaml
   - /folder1/item2.json
 + folder2/
   - /folder2/item3.yaml
   + /folder2folder2.3/
     - /folder2/folder2.3/item4.json


Library path rules
-------------------

 * Any path must start with `/`, including the root path (`/`).
 * The directory path must end with `/`.
 * The file path must end with extension (eg. `.json`).


Library service
---------------

.. autoclass:: LibraryService


Example of the use:

.. code:: python

    import asab

    class MyApplication(asab.Application):

        def __init__(self):
            super().__init__()

            # Initialize the library service 
            self.LibraryService = asab.library.LibraryService(self, "LibraryService")
            self.PubSub.subscribe("ASABLibrary.ready!", self.on_library_ready)

        async def on_library_ready(self, event_name, library):
            print("# Library\n")

            for item in await self.LibraryService.list("", recursive=True):
                print(" *", item)
                if item.type == 'item':
                    itemio = await self.LibraryService.read(item.name)
                    if itemio is not None:
                        with itemio:
                            content = itemio.read()
                            print("  - content: {} bytes".format(len(content)))
                    else:
                        print("  - (DISABLED)")


.. automethod:: LibraryService.read

.. automethod:: LibraryService.list

.. automethod:: LibraryService.export



Notification of changes
-----------------------


.. automethod:: LibraryService.subscribe



Providers
---------

.. py:currentmodule:: asab.library.providers

The library can be configured to work with following "backends" (aka providers):


Filesystem
^^^^^^^^^^

.. py:currentmodule:: asab.library.providers.filesystem

.. autoclass:: FileSystemLibraryProvider
    :no-undoc-members:


Apache Zookeeper
^^^^^^^^^^^^^^^^

.. py:currentmodule:: asab.library.providers.zookeeper

.. autoclass:: ZooKeeperLibraryProvider
    :no-undoc-members:


Microsoft Azure Storage
^^^^^^^^^^^^^^^^^^^^^^^

.. py:currentmodule:: asab.library.providers.azurestorage

.. autoclass:: AzureStorageLibraryProvider
    :no-undoc-members:


Git repository
^^^^^^^^^^^^^^

.. py:currentmodule:: asab.library.providers.git

.. autoclass:: GitLibraryProvider
    :no-undoc-members:



Layers
------

The library content can be organized into unlimmited number of layers.
Each layer is represented by a `provider` with a specific configuration.


Library configuration
---------------------


Example:

.. code:: ini

    [library]
    providers:
        provider+1://...
        provider+2://...
        provider+3://...

