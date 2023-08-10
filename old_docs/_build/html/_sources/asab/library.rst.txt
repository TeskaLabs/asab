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

Example of the library structure:

.. code:: 

 + /folder1/
   - /folder1/item1.yaml
   - /folder1/item2.json
 + /folder2/
   - /folder2/item3.yaml
   + /folder2folder2.3/
     - /folder2/folder2.3/item4.json


Library path rules
-------------------

* Any path must start with `/`, including the root path (`/`).
* The folder path must end with `/`.
* The item path must end with extension (eg. `.json`).


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
            self.PubSub.subscribe("Library.ready!", self.on_library_ready)

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

Connection to git repositories requires `pygit2 <https://www.pygit2.org/>`_ library to be installed.

Example of configuration:

.. code:: ini

    [library]
    providers: git+https://github.com/john/awesome_project.git

Functionality
~~~~~~~~~~~~~

The git provider clones the repository into a temporary directory and then uses the File System Provider to read the files from it. The default path for the cloned repository is `/tmp/asab.library.git/` and it can be changed manually:

.. code:: ini

    [library:git]
    repodir=path/to/repository/cache


Deploy tokens in GitLab
~~~~~~~~~~~~~~~~~~~~~~~
GitLab uses deploy tokens to enable authentication of deployment tasks, independent of a user account. A `deploy token` is an SSH key that grants access to a single repository. The public part of the key is attached directly to the repository instead of a personal account, and the private part of the key remains on the server. It is the preferred preferred way over changing local SSH settings.

If you want to create a deploy token for your GitLab repository, follow these steps from the `manual <https://docs.gitlab.com/ee/user/project/deploy_tokens/#create-a-deploy-token>`_:

1. Go to **Settings > Repository > Deploy tokens** section in your repository. (Note that you have to possess "Maintainer" or "Owner" role for the repository.)
2. Expand the "Deploy tokens" section. The list of current Active Deploy Tokens will be displayed. 
3. Complete the fields and scopes. We recommend to specify custom "username", as you will need it later for the url in configuration.
4. Record the deploy token's values *before leaving or refreshing the page*! After that, you cannot access it again.

After the deploy token is created, use the URL for repository in the following format:

.. code::

    https://<username>:<deploy_token>@gitlab.example.com/john/awesome_project.git

Reference
~~~~~~~~~

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


PubSub messages
---------------

.. option:: Library.ready!

.. option:: Library.change!
