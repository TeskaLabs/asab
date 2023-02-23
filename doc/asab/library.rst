.. _library-ref:

Library
=======

.. py:currentmodule:: asab.library

The ASAB Library (`asab.library`) is a concept of the shared data content across microservices.
The `asab.library` is read-only interface for listing and reading this content.
The library can also notify the ASAB microservice about changes in underlaying library, eg. for automated update/reload.

The library content is organized in simplified filesystem manner, with directories and files.

There is a companion microservice `asab-library` that can be used for management and editation of the content.
The `asab.library` can however operate without `asab-library`.


Library structure
-----------------


.. code:: 

	+ /folder1/
	  - /folder1/item1.yaml
	  - /folder1/item2.json
	+ folder2
	  - /folder2/item3.yaml
	  + folder2.3
	    - /folder2/folder2.3/item4.json


Path rules
----------

 * The path must start with `/`, including the root path (`/`).
 * The directory path must end with `/`.
 * The file path must end with extension (eg. `.json`).

Library service
---------------

.. py:class:: LibraryService


.. code:: python

	import asab

	class MyApplication(asab.Application):

		def __init__(self):
			super().__init__()

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


.. py:method:: LibraryService.read(self, path: str, tenant: str = None)

.. py:method:: LibraryService.list(self, path="/", tenant=None, recursive=False)

.. py:method:: LibraryService.export(self, path="/", tenant=None, remove_path=False)



Notification of changes
---------------------------------------

.. py:method:: LibraryService.subscribe(self, paths)



Providers
---------

The library can be configured to work with following "backends" (aka providers):

* Filesystem
* Apache Zookeeper
* Microsoft Azure Storage
* git repository


Layers
------

The library content can be organized into unlimmited number of layers.
Each layer is represented by a `provider` with a specific configuration.



Reference
---------

.. automodule:: asab.library
    :members:
    :undoc-members:
    :show-inheritance:
