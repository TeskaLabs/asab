import os
import logging
import aiohttp
import aiohttp.web

import asab
import asab.web
import asab.api
import asab.api.discovery
import asab.zookeeper

# `instance_id`` and `service_id` are identificators set as environemnt variables.
# ASAB miroservices are meant to run in separate (Docker) containers.
instance_id = "my_application_{}".format(os.getpid())
os.environ["INSTANCE_ID"] = instance_id
os.environ["SERVICE_ID"] = "service-discovery-demo"

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		"web": {
			"listen": "8090",
		},

		"zookeeper": {
			"path": "example2",
			"servers": "zookeeper-1:2181"
		},
	}
)


class ServiceDiscoveryDemoApplication(asab.Application):

	async def initialize(self):
		# Initialize web server
		self.add_module(asab.web.Module)
		websvc = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(websvc, "web")

		# Initialize zookeeper
		self.add_module(asab.zookeeper.Module)
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")
		self.ZooKeeperContainer = asab.zookeeper.ZooKeeperContainer(self.ZooKeeperService, "zookeeper")

		# The DiscoverySession is functional only with ApiService initialized.
		self.ASABApiService = asab.api.ApiService(self)
		self.ASABApiService.initialize_web(self.WebContainer)
		self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)

		self.DiscoveryService = self.get_service("asab.DiscoveryService")

		self.WebContainer.WebApp.router.add_get('/locate', self.locate_self)
		self.WebContainer.WebApp.router.add_get('/hello', self.hello)

		self.PubSub.subscribe("Application.tick/10!", self._on_tick10)


	async def _on_tick10(self, event_name):
		discover = await self.DiscoveryService.discover()
		print("Discovered services:", len(discover))
		# pprint.pprint(discover)


	async def locate_self(self, request):
		# This method seeks for this application in the ZooKeeper. Thus, it calls itself, being a tiny Oroboros.
		# Try to run more than one ASAB Application with the same ZooKeeper configuration.
		# You will get a tool to locate any service in the "cluster".

		# Get config of the application:
		config = None
		async with self.DiscoveryService.session() as session:
			try:
				# use URL in format: <protocol>://<value>.<key>.asab/<endpoint> where key is "service_id" or "instance_id" and value the respective service identificator
				async with session.get("http://service-discovery-demo.service_id.asab/hello") as resp:
					if resp.status == 200:
						config = await resp.json()
			except asab.api.discovery.NotDiscoveredError as e:
				L.error(e)

		if config is None:
			return aiohttp.web.json_response({"result": "FAILED"})

		return aiohttp.web.json_response(config)


	async def hello(self, request):
		return aiohttp.web.json_response({"result": "Hello, world!"})


if __name__ == '__main__':
	app = ServiceDiscoveryDemoApplication()
	app.run()
