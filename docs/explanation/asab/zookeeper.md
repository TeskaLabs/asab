Zookeeper {#zookeeper-ref}
=========

The [asab.zookeeper]{.title-ref} is a [Apache
Zookeeper](https://zookeeper.apache.org) asynchronous client based on
[Kazoo](https://github.com/python-zk/kazoo) library.

Apache ZooKeeper is a distributed coordination service that provides a
hierarchical key-value data store, called a znode tree, to store and
manage configuration, coordination, and synchronization data. The znode
tree is similar to a file system tree, where each znode is like a file
or a directory.

Apache ZooKeeper can be used to design microservices in a stateless
manner by managing and coordinating the state information between
microservices. In this design, each microservice does not store any
state information, but instead relies on ZooKeeper for state management.

Zookeeper container
-------------------

A Zookeeper container represents a connectivity to Apache Zookeeper
server(s). The application can operate multiple instances of Zookeeper
container.

This code illustrates the typical way how to create Zookeeper container:

``` {.python}
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
        self.PubSub.subscribe("ZooKeeperContainer.state/CONNECTED!", self._on_zk_connected)


    async def _on_zk_connected(self, event_name, zookeeper):
        if zookeeper != self.ZooKeeperContainer:
            return

        print("Connected to Zookeeper!")
```

# TODO: autoclass%
ZooKeeperContainer
xxx

Specifications are obtained from:

1.  [z\_path]{.title-ref} argument, which is Zookeeper URL (see below)
2.  the configuration section specified by
    [config\_section\_name]{.title-ref} argument
3.  [ASAB\_ZOOKEEPER\_SERVERS]{.title-ref} environment variable

The [z\_path]{.title-ref} argument has precedence over config but the
implementation will look at configuration if [z\_path]{.title-ref} URL
is missing completely or partially. Also, if configuration section
doesn\'t provide information about servers,
[ASAB\_ZOOKEEPER\_SERVERS]{.title-ref} environment variable is used.

### Example of configuration section

``` {.ini}
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=myfolder
```

### Example of [ASAB\_ZOOKEEPER\_SERVERS]{.title-ref} environment variable

``` {.ini}
ASAB_ZOOKEEPER_SERVERS=zookeeper-1:2181,zookeeper-2:2181
```

### Supported types of [z\_path]{.title-ref} URLs

1.  Absolute URL

    > [zookeeper://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/etc/configs/file1]{.title-ref}
    >
    > The URL contains all information for a connectivity.

2.  URL without servers with absolute path

    > [zookeepers:///etc/configs/file1]{.title-ref}
    >
    > In this case the relative url is expanded as follows:
    > [zookeeper://{zookeeper\_servers}/etc/configs/file1]{.title-ref}
    >
    > Where [{zookeeper\_servers}]{.title-ref} is substituted with the
    > [servers]{.title-ref} entry of the \[zookeeper\] configuration
    > file section.

3.  URL without servers with relative path

    > [zookeeper:./etc/configs/file1]{.title-ref}
    >
    > In this case, the relative URL is expanded as follows:
    > [zookeper://{zookeeper\_servers}/{zookeeper\_path}/etc/configs/file1]{.title-ref}
    >
    > Where {zookeeper\_servers} is substituted with the
    > [servers]{.title-ref} entry of the \[zookeeper\] configuration
    > file section and {zookeeper\_path} is substituted with the
    > \"path\" entry of the \[zookeeper\] configuration file section.

# TODO: automethod%
ZooKeeperContainer.is\_connected
xxx

Reading from Zookeeeper
-----------------------

# TODO: automethod%
ZooKeeperContainer.get\_children
xxx

# TODO: automethod%
ZooKeeperContainer.get\_data
xxx

# TODO: automethod%
ZooKeeperContainer.get\_raw\_data
xxx

Advertisement into Zookeeper
----------------------------

# TODO: automethod%
ZooKeeperContainer.advertise
xxx

PubSub messages
---------------

%TODO: option%
ZooKeeperContainer.state/CONNECTED!
xxx

%TODO: option%
ZooKeeperContainer.state/LOST!
xxx

%TODO: option%
ZooKeeperContainer.state/SUSPENDED!
xxx

When a Zookeeper connection is first created, it is in the LOST state.
After a connection is established it transitions to the CONNECTED state.
If any connection issues come up or if it needs to connect to a
different Zookeeper cluster node, it will transition to SUSPENDED to let
you know that commands cannot currently be run. The connection will also
be lost if the Zookeeper node is no longer part of the quorum, resulting
in a SUSPENDED state.

Upon re-establishing a connection the client could transition to LOST if
the session has expired, or CONNECTED if the session is still valid.

For mor info, visit:
<https://kazoo.readthedocs.io/en/latest/basic_usage.html#understanding-kazoo-states>

Kazoo
-----

Kazoo is the synchronous Python library for Apache Zookeeper.

It can be used directly for a more complicated tasks. Kazoo
[client]{.title-ref} is accessible at
[ZooKeeperContainer.ZooKeeper.Client]{.title-ref}. Synchronous methods
of Kazoo client must be executed using [ProactorService]{.title-ref}.

Here is the example:

``` {.python}
def write_to_zk():
   self.ZooKeeperContainer.ZooKeeper.Client.create(path, data, sequence=True, ephemeral=True, makepath=True)

await self.ZooKeeperContainer.ZooKeeper.ProactorService.execute(write_to_zk)
```
