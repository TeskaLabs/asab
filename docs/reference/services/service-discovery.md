# Discovery Service

Service discovery enables communication among multiple ASAB microservices in a server cluster. Each microservice can search for and find address to API interface (URL) of any other service within the cluster.

In service discovery, there are two main roles: the "server" and the "client."

The server advertises its "position" in the cluster and provides an API for communication. The client uses this API to interact with the server.

In the context of service discovery, all microservices in the cluster act as both servers and clients.

## Prerequisites

Following requirements must be fulfilled:

- Zookeeper connection and configuration must be the same for all services in the cluster.
- Zookeeper container must be initialized in the service.
- `asab.WebService` and `asab.WebContainer` must be initialized.
- `asab.APIService` must be initialized.
- Environment variables `NODE_ID`, `SERVICE_ID` and `INSTANCE_ID` must be set.
- `INSTANCE_ID` (or hostname if `INSTANCE_ID` is missing) must be resolvable.

## Server - Advertising into ZooKeeper

Even though the service can provide multiple communication interfaces, major use case is the web API.

A "server" application has to provide the API and advertise its address into a consensus technlogy - ZooKeeper.

### Application requirements

Services inside the application must be initialized in the right order.

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
		self.ASABApiService.initialize_web(self.WebContainer)
		self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)
```

### Configuration

ZooKeeper configuration must be the same for all services in the cluster. Port can be set in the configuration.

```ini title="myapp.conf"
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181

[web]
listen=0.0.0.0 8090
```

### Environment variables

The discovery is based on provided "ids". Use either a set of specific ids provided as environemntal variable, or create [custom discovery ids](#custom-discovery-ids) within the application.

Pre-cast ids used for service discovery. Provide them as environment variables:

| Variable | Description | Example |
| --- | --- | --- |
| `SERVICE_ID` | Identifier of the ASAB microservice. | my-app |
| `INSTANCE_ID` | Identifier of a specific instance of the ASAB microservice. | my-app-1, my-app-2, ... |
| `NODE_ID` | Identifier of a cluster node. | node-1, node-2, ... |

!!! warning "Instance ID must be resolvable"

	ASAB framework cannot set up networking. In order to enable service discovery, `INSTANCE_ID` of a service must be resolavable from the client. If `INSTANCE_ID` is missing, hostname is taken instead and then, hostname must be resolvable.


### Information advertised

When all requirements of a server-side microservice are fullfilled, the service advertises into the consensus a unique information bound to its runtime.

The file of JSON format contains information describing the running application.


```json title="asab/run/ASABMyApplication.0000090098"
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

## Client - Using Service Discovery

All services are being "server" and "client" at the same time. This paragraph describes how to discover (as a client) a service in the cluster.

### Call API using DiscoveryService.session()

Once the service propagates itself into ZooKeeper, other services in the cluster can use its API.

`DiscoveryService` provides a method `session()` which inherits from `aiohttp.ClientSession`. It can be used the same way as `aiohttp.ClientSession`. Instead of explicit URL, use URL with `asab` domain.

The URL is constructed in the format `http://<value>.<key>.asab/...` where _key_ is the name of the identifier (e.g. `instance_id`, `service_id`) and _value_ is its value (e.g. `my_app_1`)

!!! example

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

			# The DiscoverySession is functional only with ApiService initialized.
			self.ASABApiService = asab.api.ApiService(self)
			self.ASABApiService.initialize_web(self.WebContainer)
			self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)

			self.DiscoveryService = self.get_service("asab.DiscoveryService")
		
		async def main(self):
			async with self.DiscoveryService.session() as session: 
				try:
					# use URL in format: <protocol>://<value>.<key>.asab/<endpoint> where key is "service_id" or "instance_id" and value the respective service identificator
					async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
						if resp.status == 200:
							config = await resp.json()
				except asab.api.discovery.NotDiscoveredError as e:
					L.error(e)
	```

!!! warning

	`asab.DiscoveryService` is functional only with `ApiService` initialized. That means, `WebContainer` and `ZooKeeperContainer` must be also present in the application.

!!! warning

	Discovery Service searches for microservices in the same ZooKeeper path as defined in the configuration. Therefore, all services in the cluster should be configured with the same ZooKeeper path.


### locate()

Returns set of URLs based on an id of a service. Provide the filter as a dictionary. The keys of the dictionary can be `node_id`, `service_id`, `instance_id` or [custom ids](#custom-discovery-ids).

!!! example

	To look for all URLs of a service called `very-nice-service`, use inside the application:
	```python
	await self.DiscoveryService.locate({"service_id": "very-nice-service"})
	```
	It returns a set of values, URLs. E.g.
	```
	{"http://very-nice-service-1:8888", "http://very-nice-service-2:8889"}
	```

### discover()

Returns a dictionary with all known services, organized by their ids and information on how to resolve them.

!!! example

	```python
	await self.DiscoveryService.discover()
	```


## Custom discovery ids

Custom identifiers can be set during runtime.

!!! example

	Inside the application, when Api Service is already initialized:

	```python

	self.ASABApiService.update_discovery({"custom_id": ["id1", "id2", "id3"]})
	```

	The argument of the method must be a dictionary, where key is string and value is a list.
	The `custom_id` can be used in both discovery [session](#call-api-using-discoveryservicesession) and [`locate()`](#locate) method.


## Using service discovery during authorization

When using authorization server e.g. SeaCat Auth to provide authorization for each API call, it can be also found in the cluster through service discovery. In order to connect `asab.AuthService` with the service discovery, several requiremetns must be met:

- API Service must be fully initiliazed BEFORE Auth Service.
- Authorization server (SeaCat Auth) must be present in the cluster, resolvable by its instance id, and advertising itself into the ZooKeeper (being server itself).
- `[auth]` configuration section must contain URL recognizable by the service discovery.

!!! example "Auth Service using service discovery"

	API Service must be fully initiliazed BEFORE Auth Service.

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

			# The DiscoverySession is functional only with ApiService initialized.
			self.ASABApiService = asab.api.ApiService(self)
			self.ASABApiService.initialize_web(self.WebContainer)
			self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)

			self.DiscoveryService = self.get_service("asab.DiscoveryService")

			# Initialize authorization after ASABApiService.initialize_zookeeper() to get DiscoveryService into auth module
			self.AuthService = asab.web.auth.AuthService(self)
			self.AuthService.install(self.WebContainer)
	```

	`[auth]` configuration section must contain URL recognizable by the service discovery.
	
	```ini title="my_app.conf"
	[auth]
	"public_keys_url": "http://seacat-auth.service_id.asab/.well-known/jwks.json"
	```


## Reference

::: asab.api.discovery
