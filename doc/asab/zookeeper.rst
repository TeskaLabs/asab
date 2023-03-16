.. _zookeeper-ref:

Zookeeper
=========

.. py:currentmodule:: asab.zookeeper

The `asab.zookeeper` is a `Apache Zookeeper <https://zookeeper.apache.org>`_ asynchronous client based on `Kazoo <https://github.com/python-zk/kazoo>`_ library.

Apache ZooKeeper is a distributed coordination service that provides a hierarchical key-value data store, called a znode tree, to store and manage configuration, coordination, and synchronization data. The znode tree is similar to a file system tree, where each znode is like a file or a directory.

Apache ZooKeeper can be used to design microservices in a stateless manner by managing and coordinating the state information between microservices. In this design, each microservice does not store any state information, but instead relies on ZooKeeper for state management.


Zookeeper container
-------------------

A Zookeeper container represents a connectivity to Apache Zookeeper server(s).
The application can operate multiple instances of Zookeeper container.


This code illustrates the typical way how to create Zookeeper container:

.. code:: python

    import asab.zookeeper

    class MyApplication(asab.Application):

        def __init__(self):
            ...

            # Load the ASAB Zookeeper module
            self.add_module(asab.zookeeper.Module)

            # Initialize ZooKeeper Service
            self.ZooKeeperService = self.get_service("asab.ZooKeeperService")

            # Create the Zookeeper container
            self.ZooKeeperContainer = asab.zookeeper.ZooKeeperContainer(self.ZooKeeperService)

            # Subscribe to Zookeeper container ready event
            self.PubSub.subscribe("ZooKeeperContainer.started!", self._on_zk_ready)


        async def _on_zk_ready(self, event_name, zookeeper):
            if zookeeper != self.ZooKeeperContainer:
                return

            print("Connected to Zookeeper!")



.. autoclass:: ZooKeeperContainer

Specifications are obtained from:

1. `z_path` argument, which is Zookeeper URL (see below)
2. the configuration section specified by `config_section_name` argument
3. `ASAB_ZOOKEEPER_SERVERS` environment variable

The `z_path` argument has precedence over config but the implementation will look
at configuration if `z_path` URL is missing completely or partially.
Also, if configuration section doesn't provide information about servers, `ASAB_ZOOKEEPER_SERVERS` environment variable is used.


Example of configuration section
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: ini

    [zookeeper]
    servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
    path=myfolder


Example of `ASAB_ZOOKEEPER_SERVERS` environment variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: ini

    ASAB_ZOOKEEPER_SERVERS=zookeeper-1:2181,zookeeper-2:2181


Supported types of `z_path` URLs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Absolute URL
    
    `zookeeper://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/etc/configs/file1`


    The URL contains all information for a connectivity.


2. URL without servers with absolute path
    
    `zookeepers:///etc/configs/file1`

    In this case the relative url is expanded as follows:
    `zookeeper://{zookeeper_servers}/etc/configs/file1`

    Where `{zookeeper_servers}` is substituted with the `servers` entry of the [zookeeper] configuration file section.


3. URL without servers with relative path

    `zookeeper:./etc/configs/file1`
    
    In this case, the relative URL is expanded as follows:
    `zookeper://{zookeeper_servers}/{zookeeper_path}/etc/configs/file1`

    Where {zookeeper_servers} is substituted with the `servers` entry of the [zookeeper] configuration file section and
    {zookeeper_path} is substituted with the "path" entry of the [zookeeper] configuration file section.



.. automethod:: ZooKeeperContainer.is_connected


Reading from Zookeeeper
-----------------------

.. automethod:: ZooKeeperContainer.get_children

.. automethod:: ZooKeeperContainer.get_data

.. automethod:: ZooKeeperContainer.get_raw_data


Advertisement into Zookeeper
----------------------------

.. automethod:: ZooKeeperContainer.advertise


PubSub messages
---------------

.. option:: ZooKeeperContainer.started!


.. option:: ZooKeeperContainer.state/CONNECTED!

.. option:: ZooKeeperContainer.state/LOST!

.. option:: ZooKeeperContainer.state/SUSPENDED!


Kazoo
-----

Kazoo is the synchronous Python library for Apache Zookeeper.

It can be used directly for a more complicated tasks.
Kazoo `client` is accessible at `ZooKeeperContainer.ZooKeeper.Client`.
Synchronous methods of Kazoo client must be executed using `ProactorService`.

Here is the example:

.. code:: python

     def write_to_zk():
        self.ZooKeeperContainer.ZooKeeper.Client.create(path, data, sequence=True, ephemeral=True, makepath=True)

    await self.ZooKeeperContainer.ZooKeeper.ProactorService.execute(write_to_zk)

