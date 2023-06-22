.. py:currentmodule:: asab.library

.. _library-ref:



Library
=======

The ASAB Library (`asab.library`) is a concept of the shared data content across microservices in the cluster.
In the cluster/cloud microservice architectures, all microservices must have access to unified resources.
The `asab.library` provides a read-only interface for listing and reading this content.

`asab.library` is designed to be read-only.
It also allows to "stack" various libraries into one view (overlayed) that merges the content of each library into one united space.

The library can also notify the ASAB microservice about changes, e.g. for automated update/reload.

There is a companion microservice `asab-library` that can be used for the management and editing of the library content.
The `asab.library` can however operate without `asab-library` microservice.


Library structure
-----------------

The library content is organized in a simplified filesystem manner, with directories and files.

Example of the library structure:

.. code::

 + /folder1/
   - /folder1/item1.yaml
   - /folder1/item2.json
 + /folder2/
   - /folder2/item3.yaml
   + /folder2/folder2.3/
	 - /folder2/folder2.3/item4.json


Library path rules
-------------------

* Any path must start with `/`, including the root path (`/`).
* The folder path must end with `/`.
* The item path must end with an extension (e.g. `.json`).

Layers
------

The library content can be organized into an unlimited number of layers.
Each layer is represented by a `provider` with a specific configuration.

The layers of the library are like slices of Swiss cheese layered on top of each other.
Only if there is a hole in the top layer can you see the layer that shows through underneath.
It means that files of the upper layer overwrite files with the same path in the lower layers.

The first provider is responsible for providing `/.disabled.yaml` that controls the visibility of items.
If `/.disabled.yaml` is not present, then is considered empty.


Library service
---------------


Example of the use:

.. code:: python

	import asab
	import asab.library


	# this substitutes configuration file
	asab.Config.read_string(
				"""
	[library]
	providers=git+https://github.com/TeskaLabs/asab-maestro-library.git
	"""
			)


	class MyApplication(asab.Application):

		def __init__(self):
			super().__init__()
			# Initialize the library service 
			self.LibraryService = asab.library.LibraryService(self, "LibraryService")
			self.PubSub.subscribe("Library.ready!", self.on_library_ready)

		async def on_library_ready(self, event_name, library):
			print("# Library\n")

			for item in await self.LibraryService.list("/", recursive=True):
				print(" *", item)
				if item.type == 'item':
					itemio = await self.LibraryService.read(item.name)
					if itemio is not None:
						with itemio:
							content = itemio.read()
							print("  - content: {} bytes".format(len(content)))
					else:
						print("  - (DISABLED)")

	if __name__ == '__main__':
		app = MyApplication()
		app.run()

The library service may exist in multiple instances, with different `paths` setups.
For that reason, you have to provide a unique `service_name` and there is no default value for that.

For more examples of Library usage, please see `ASAB examples <https://github.com/TeskaLabs/asab/tree/master/examples>`_


Library configuration
---------------------


Example:

.. code:: ini

	[library]
	providers:
		provider+1://...
		provider+2://...
		provider+3://...



PubSub messages
---------------
Read more about :ref:`PubSub<pubsub_page>` in ASAB.

.. option:: Library.ready!

A library is created in a “not ready” state.
Only after all providers are ready, the library itself becomes ready.
The library indicates that by the PubSub event `Library.ready!`.

.. option:: Library.not_ready!

The readiness of the library (connection to external technologies) can be lost. You can also subscribe to `Library.not_ready!` event.

.. option:: Library.change!

You can get `Notification on Changes`_ in the library. Specify a path or paths that you would like to "listen to". Then subscribe to `Library.change!` PubSub event.
Available for Git and FileSystem providers for now.



Notification on changes
-----------------------

.. automethod:: LibraryService.subscribe



Providers
---------

The library can be configured to work with the following "backends" (aka providers):


Filesystem
^^^^^^^^^^

The most basic provider that reads data from the local filesystem.
The notification on changes functionality is available only for Linux systems, as it implements `inotify <https://en.wikipedia.org/wiki/Inotify>`_

Configuration examples:

.. code:: ini

	[library]
	providers: /home/user/directory


.. code:: ini

	[library]
	providers: ./this_directory


.. code:: ini

	[library]
	providers: file:///home/user/directory



Apache Zookeeper
^^^^^^^^^^^^^^^^

ZooKeeper as a consensus technology is vital for microservices in the cluster.

There are several configuration strategies:

1) Configuration from [zookeeper] section.

.. code:: ini

	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/library

	[library]
	providers:
		zk://



2) Specify a path of a ZooKeeper node where only library lives.

	The library path will be `/library`.

.. code:: ini

	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk:///library


	The library path will be `/`.

.. code:: ini

	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk:///

3) Configuration from the URL in the [library] section.

.. code:: ini

	[library]
	providers:
		zk://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/library


4) Configuration from [zookeeper] section and joined `path` from [zookeeper] and [library] sections.

	The resulting path will be `/else/library`.

.. code:: ini

	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=/else

	[library]
	providers:
		zk://./library


If a `path` from the [zookeeper] section is missing, an application class name will be used
E.g. `/BSQueryApp/library`


Microsoft Azure Storage
^^^^^^^^^^^^^^^^^^^^^^^

Reads from the Microsoft Azure Storage container.

Configuration:

.. code:: ini

	[library]
	providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER


If Container Public Access Level is not set to "Public access",
then "Access Policy" must be created with "Read" and "List" permissions
and "Shared Access Signature" (SAS) query string must be added to a URL in a configuration:

.. code:: ini

	[library]
	providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER?sv=2020-10-02&si=XXXX&sr=c&sig=XXXXXXXXXXXXXX



Git repository
^^^^^^^^^^^^^^

Connection to git repositories requires `pygit2 <https://www.pygit2.org/>`_ library to be installed.

Configuration:

.. code:: ini

	[library]
	providers: git+https://github.com/john/awesome_project.git


Deploy tokens in GitLab
~~~~~~~~~~~~~~~~~~~~~~~
GitLab uses deploy tokens to enable authentication of deployment tasks, independent of a user account.
Authentication through deploy tokens is the only supported option for now.

If you want to create a deploy token for your GitLab repository, follow these steps from the `manual <https://docs.gitlab.com/ee/user/project/deploy_tokens/#create-a-deploy-token>`_:

1. Go to **Settings > Repository > Deploy tokens** section in your repository. (Note that you have to possess a "Maintainer" or "Owner" role for the repository.)
2. Expand the "Deploy tokens" section. The list of current Active Deploy Tokens will be displayed. 
3. Complete the fields and scopes. We recommend a custom "username", as you will need it later for the URL in the configuration.
4. Record the deploy token's values *before leaving or refreshing the page*! After that, you cannot access it again.

After the deploy token is created, use the URL for the repository in the following format:

.. code:: ini

	[library]
	providers: git+https://<username>:<deploy_token>@gitlab.example.com/john/awesome_project.git


Where does the repository clone?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The git provider clones the repository into a temporary directory. The default path for the cloned repository is `/tmp/asab.library.git/` and it can be changed manually:

.. code:: ini

	[library:git]
	repodir=path/to/repository/cache


Reference
^^^^^^^^^
.. autoclass:: LibraryService

	.. automethod:: read

	.. automethod:: list

	.. automethod:: export

