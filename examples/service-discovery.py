import logging
import aiohttp
import aiohttp.web

import asab
import asab.web
import asab.api
import asab.api.discovery
import asab.zookeeper

import os

# `instance_id`` and `service_id` are identificators set as environemnt variables.
# ASAB miroservices are meant to run in separate (Docker) containers.
os.environ["INSTANCE_ID"] = "my_application_1"

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		"web": {
			"listen": "0.0.0.0 8089",
		},

		"zookeeper": {
			"path": "example",
			"servers": "localhost:2181"
		},
	}
)


class MyApplication(asab.Application):

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

	async def locate_self(self, request):
		# This method seeks for this application in the ZooKeeper. Thus, it calls itself, being a tiny Oroboros.
		# Try to run more than one ASAB Application with the same ZooKeeper configuration.
		# You will get a tool to locate any service in the "cluster".

		# Get config of the application:
		config = None
		async with self.DiscoveryService.session() as session:
			try:
				# use URL in format: <protocol>://<value>.<key>.asab/<endpoint> where key is "service_id" or "instance_id" and value the respective serivce identificator
				async with session.get("http://my_application_1.instance_id.asab/asab/v1/config") as resp:
					if resp.status == 200:
						config = await resp.json()
			except asab.api.discovery.NotDiscoveredError as e:
				L.error(e)

		if config is None:
			return aiohttp.web.json_response({"result": "FAILED"})

		return aiohttp.web.json_response(config)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
