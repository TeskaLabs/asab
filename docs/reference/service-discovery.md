# Discovery Service

Service Discovery Service is used for the communication between multiple ASAB microservices in a server cluster.

In order to work, the following requirements must be fulfilled:

- Zookeeper connection and configuration must be the same for all services in the cluster.
- Zookeeper container must be initialized in the service.
- `asab.WebService` and `asab.WebContainer` must be initialized.
- `asab.APIService` must be initialized.
- Environment variables `NODE_ID`, `SERVICE_ID` and `INSTANCE_ID` must be set.


## Advertising services into Zookeeper

### API Configuration

In order to propagate information about a microservice into Zookeeper, you need to include configuration for the web and Zookeeper containers.

```ini title="myapp.conf"
[web]
listen=0.0.0.0 8090

[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=example
```

### Environment variables setup

Every microservice should run in environment where the following variables are set:

| Variable | Description | Example |
| --- | --- | --- |
| `SERVICE_ID` | Identifier of the ASAB microservice. | my-app |
| `INSTANCE_ID` | Identifier of a specific instance of the ASAB microservice. | my-app-1, my-app-2, ... |
| `NODE_ID` | Identifier of a cluster node. | node-1, node-2, ... |

### Initializing API Service

```python
class MyApp(asab.Application):
	def __init__(self):
		super.__init__(self)
		# Initialize web server
		self.add_module(asab.web.Module)
		websvc = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(websvc, "web")

		# Initialize zookeeper
		self.add_module(asab.zookeeper.Module)
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")
		self.ZooKeeperContainer = asab.zookeeper.ZooKeeperContainer(
			self.ZooKeeperService, "zookeeper"
		)

		# Initialize ApiService
		self.ASABApiService = asab.api.ApiService(self)
		self.ASABApiService.initialize_web(self.WebContainer) #(1)!
		self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer) #(2)!
```

Propagate the information about microservice to Zookeeper.

### Information advertised

!!! example "Example of data being advertised into Zookeeper"

	```json title="zookeeper-path/run/ASABMyApplication.0000090098"
	{
		"host": "server-name-1",
		"appclass": "MyApp",
		"node_id": "node-1",
		"service_id": "my-app",
		"instance_id": "my-app-1",
		"launch_time": "2023-12-01T10:52:29.656397Z",
		"process_id": 1,
		"containerized": true,
		"created_at": "2023-11-23T11:08:22.454248Z",
		"version": "v23.47-alpha",
		"CI_COMMIT_TAG": "v23.47-alpha",
		"CI_COMMIT_REF_NAME": "v23.47-alpha",
		"CI_COMMIT_SHA": "...",
		"CI_COMMIT_TIMESTAMP": "2023-11-23T11:00:48+00:00",
		"CI_JOB_ID": "...",
		"CI_PIPELINE_CREATED_AT": "2023-11-23T11:06:40Z",
		"CI_RUNNER_ID": "..",
		"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64",
		"web": [
			[
				"0.0.0.0",
				8090
			]
		]
	}
	```

## Using Service Discovery

Once the service propagates itself into Zookeeper, it is possible for other services in the same server cluster to use its API.

`DiscoveryService` provides a method `session()` which is derived from `aiohttp.ClientSession` and is used like a context manager, see the example below.

The URL is constructed in the format `<value>.<key>.asab`

!!! example "Example of use"

	```python
	class MyApp(asab.Application):
		async def initialize(self):
			# Initialize web and zookeeper
			...

			# The DiscoverySession is functional only with ApiService initialized.
			self.ASABApiService = asab.api.ApiService(self)
			self.ASABApiService.initialize_web(self.WebContainer)
			self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)

			self.DiscoveryService = self.get_service("asab.DiscoveryService")
		
		async def main(self):
			async with self.DiscoveryService.session() as session:  #(1)!
				try:
					# use URL in format: <protocol>://<value>.<key>.asab/<endpoint> where key is "service_id" or "instance_id" and value the respective service identificator
					async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
						if resp.status == 200:
							config = await resp.json()
				except asab.api.discovery.NotDiscoveredError as e:
					L.error(e)
	```

	1. `DiscoveryService.session()` is 

!!! warning

	`asab.DiscoveryService` is functional only with `ApiService` initialized. That means, `WebContainer` and `ZooKeeperContainer` must be also present in the application.

!!! warning

	Discovery Service searches for microservices in the same Zookeeper path as defined in the configuration. Therefore, all services in the cluster should be configured with the same Zookeeper path.


## Reference

::: asab.api.discovery
