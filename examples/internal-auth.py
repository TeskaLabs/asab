#!/usr/bin/env python3

"""
You need to run two instances of this mini app, each on a different port:

INSTANCE_ID=app-1 PORT=8081 TARGET=http://app-2.instance_id.asab python examples/internal-auth.py
INSTANCE_ID=app-2 PORT=8082 TARGET=http://app-1.instance_id.asab python examples/internal-auth.py

curl http://localhost:8081/send
"""

import asab.web.rest
import asab.web.auth
import asab.zookeeper
import typing
import os

if "web" not in asab.Config:
	asab.Config["web"] = {
		"listen": os.environ.get("PORT"),
	}

if "zookeeper" not in asab.Config:
	asab.Config["zookeeper"] = {
		"servers": "localhost:2181",
	}


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		self.add_module(asab.zookeeper.Module)

		# Initialize web container
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		from asab.api import ApiService
		self.ApiService = ApiService(self)
		self.ApiService.initialize_web(self.WebContainer)

		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")
		self.ZooKeeperContainer = asab.zookeeper.ZooKeeperContainer(self.ZooKeeperService, "zookeeper")
		self.ApiService.initialize_zookeeper(self.ZooKeeperContainer)

		self.DiscoveryService = self.get_service("asab.DiscoveryService")

		# Initialize authorization
		self.AuthService = asab.web.auth.AuthService(self)
		self.AuthService.install(self.WebContainer)

		# Add routes
		self.WebContainer.WebApp.router.add_put("/send", self.send)
		self.WebContainer.WebApp.router.add_put("/receive", self.receive)

		self.Name = os.environ.get("INSTANCE_ID")
		self.Target = os.environ.get("TARGET")

	@asab.web.auth.noauth
	async def send(self, request):
		"""
		Send a request to the /receive endpoint of the TARGET application.
		Return the log of this exchange.
		"""
		log = ["{} received request.".format(self.Name)]
		async with self.DiscoveryService.session(auth="internal") as session:
			async with session.put(
				"{}/receive".format(self.Target.rstrip("/")),
				json=log
			) as resp:
				log = await resp.json()
				if resp.status != 200:
					log.append("{} received error response.".format(self.Name))
					return asab.web.rest.json_response(request, log)
				log.append("{} received response.".format(self.Name))
				return asab.web.rest.json_response(request, log)

	@asab.web.rest.json_schema_handler({"type": "array"})
	async def receive(self, request, *, json_data):
		"""
		Receive an array, append message and return it.
		"""
		json_data.append("{} received request.".format(self.Name))
		return asab.web.rest.json_response(request, json_data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
