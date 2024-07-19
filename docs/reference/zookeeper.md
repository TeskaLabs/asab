# ZooKeeper

`asab.zookeeper` is an [Apache ZooKeeper](https://zookeeper.apache.org) asynchronous client based on [Kazoo](https://github.com/python-zk/kazoo) library.

Apache ZooKeeper is a distributed coordination service that provides a hierarchical key-value data store, 
called a **znode tree**, to store and manage configuration, coordination, and synchronization data.
The znode tree is similar to a file system tree, where each znode is like a file or a directory.

Apache ZooKeeper can be used to design microservices in a stateless manner by managing and coordinating the state information between microservices.
In this design, each microservice does not store any state information, but instead relies on ZooKeeper for state management.

## ZooKeeper container

A ZooKeeper container represents a connectivity to Apache ZooKeeper server(s).
The application can operate multiple instances of ZooKeeper container.

This code illustrates the typical way of creating a ZooKeeper container:

``` python
import asab.zookeeper

class MyApplication(asab.Application):

	async def initialize(self):
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

Specifications are obtained from:

1. `z_path` argument, which is Zookeeper URL (see below)
2. The configuration section specified by `config_section_name` argument
3. `$ASAB_ZOOKEEPER_SERVERS` environment variable

The `z_path` argument has precedence over config but the implementation will
look at configuration if `z_path` URL is missing completely or partially.
Also, if configuration section doesn't provide information about servers,
`ASAB_ZOOKEEPER_SERVERS` environment variable is used.

!!! example "Example of configuration section"

	``` ini
	[zookeeper]
	servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
	path=myfolder
	```

!!! example "Example of `$ASAB_ZOOKEEPERS_SERVERS` environment variable"

	``` ini
	ASAB_ZOOKEEPER_SERVERS=zookeeper-1:2181,zookeeper-2:2181
	```

### Supported types of `z_path` URLs

1. Absolute URL:

	``` ini
	zookeeper://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/etc/configs/file1
	```
	The URL contains all information for a connectivity.

2. URL without servers with absolute path:

	``` ini
	zookeepers:///etc/configs/file1
	```
	In this case the relative url is expanded as follows:

	```ini
	zookeeper://{zookeeper_servers}/etc/configs/file1
	```
	Where `{zookeeper_servers}` is substituted with the `servers` entry of the `[zookeeper]` configuration file section.

3.  URL without servers with relative path

	```ini
	zookeeper:./etc/configs/file1
	```
	
	In this case, the relative URL is expanded as follows: 

	```ini
	zookeper://{zookeeper_servers}/{zookeeper_path}/etc/configs/file1
	```

	Where `{zookeeper_servers}` is substituted with the servers entry of the `[zookeeper]` configuration file section
	a nd `{zookeeper_path}` is substituted with the "path" entry of the `[zookeeper]` configuration file section.


## Reading from ZooKeeeper

TODO

## PubSub messages

ZooKeeperContainer.state/CONNECTED!

ZooKeeperContainer.state/LOST!

ZooKeeperContainer.state/SUSPENDED!

When a Zookeeper connection is first created, it is in the LOST state.
After a connection is established, it transitions to the CONNECTED state.
If any connection issues come up, or if it needs to connect to a
different Zookeeper cluster node, it will transition to SUSPENDED to let
you know that commands cannot currently be run. The connection will also
be lost if the Zookeeper node is no longer part of the quorum, resulting
in a SUSPENDED state.

Upon re-establishing a connection, the client could transition to LOST if
the session has expired, or CONNECTED if the session is still valid.

For more info, visit (https://kazoo.readthedocs.io/en/latest/basic_usage.html#understanding-kazoo-states)

## Kazoo

Kazoo is the synchronous Python library for Apache Zookeeper.

It can be used directly for more complicated tasks. Kazoo `client` is accessible at `ZooKeeperContainer.ZooKeeper.Client`.
Synchronous methods of Kazoo client must be executed using `ProactorService`.

!!! example
	``` python
	def write_to_zk():
	self.ZooKeeperContainer.ZooKeeper.Client.create(path, data, sequence=True, ephemeral=True, makepath=True)

	await self.ZooKeeperContainer.ZooKeeper.ProactorService.execute(write_to_zk)
	```
