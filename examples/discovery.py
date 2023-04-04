import logging
import aiohttp
import aiohttp.web

import asab
import asab.web
import asab.api
import asab.zookeeper

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

		# Service Discovery is part of ApiService and needs its full functionality
		self.ASABApiService = asab.api.ApiService(self)
		self.ASABApiService.initialize_web(self.WebContainer)
		self.ASABApiService.initialize_zookeeper(self.ZooKeeperContainer)

		# Localize Service Discovery Service
		self.DiscoveryService = self.get_service("asab.DiscoveryService")

		self.WebContainer.WebApp.router.add_get('/locate', self.locate_self)

	async def locate_self(self, request):
		# This method seeks for MyApplication in the ZooKeeper. Thus, it calls itself, being a tiny Oroboros.
		# Try to run more than one ASAB Application with the same ZooKeeper configuration.
		# You will get a tool to locate any service in the "cluster".

		# Get config of the application:
		config = None
		session = await self.DiscoveryService.session()
		try:
			async with session.get("http://MyApplication.appclass/asab/v1/config") as resp:
				if resp.status == 200:
					config = await resp.json()

		finally:
			await session.close()

		if config is None:
			return aiohttp.web.json_response({"result": "FAILED"})

		return aiohttp.web.json_response(config)


if __name__ == '__main__':
	app = MyApplication()
	app.run()
