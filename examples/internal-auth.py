#!/usr/bin/env python3

"""
This example expects a zookeeper instance to be running at localhost:2181.

You need to run two instances of this mini app, each on a different port.
I recommend running them in two separate terminals, to easily observe the output:

Terminal 1
```sh
INSTANCE_ID=app-1 PORT=8081 TARGET=http://app-2.instance_id.asab AUTO_SEND=TRUE python examples/internal-auth.py
```

Terminal 2
```sh
INSTANCE_ID=app-2 PORT=8082 TARGET=http://app-1.instance_id.asab python examples/internal-auth.py
```

The first app will send a message to the other app every ten seconds and print the response.

You can also make PUT request to the /send_to_target endpoint of either app to make
it communicate with the other app and forward you the response:

	curl -XPUT -H "X-Tenant: gummybear-corp" --data "hello!" http://localhost:8081/send_to_target

"""
import random
import os
import aiohttp.web

import asab.web.rest
import asab.web.auth
import asab.zookeeper
import asab.contextvars
import asab.api.discovery

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
		self.WebContainer.WebApp.router.add_put("/send_to_target", self.send)
		self.WebContainer.WebApp.router.add_put("/receive", self.receive)
		if os.environ.get("AUTO_SEND"):
			self.PubSub.subscribe("Application.tick/10!", self._on_tick)

		self.Name = os.environ.get("INSTANCE_ID")
		self.Target = os.environ.get("TARGET")


	async def _send(self, message, tenant):
		"""
		Use discovery session to send message to requested tenant in the TARGET app.
		"""
		if tenant:
			print("Sending message to tenant {!r}: {}".format(tenant, message))
		else:
			print("Sending message: {}".format(message))

		try:
			async with self.DiscoveryService.session(base_url=self.Target, auth="internal", tenant=tenant) as session:
				async with session.put("/receive", data=message) as resp:
					text = await resp.text()
					if resp.status != 200:
						print("Received error response: {!r}".format(text))
						return None
					return text
		except asab.api.discovery.NotDiscoveredError:
			print("Failed to discover target {!r}".format(self.Target))
			return None


	async def _on_tick(self, message_type):
		"""
		Send message to a random tenant in the TARGET app and print the response
		"""
		message = random.choice(["Hey friend!", "Wazzup!?", "Howdy!", "Hello:)", "Hiiiiii^^", "Greetings."])
		tenant = random.choice([None, "mangos-inc", "potato-corp", "strawberry-and-co", "cabbage-io"])

		response = await self._send(message, tenant)
		print("Server replied with: {!r}".format(response))


	# @asab.web.auth.noauth  # Enable this to be able to send requests without authorization
	async def send(self, request):
		"""
		Send a request to the /receive endpoint of the TARGET application.
		"""
		message = await request.text()
		tenant = request.headers.get("X-Tenant")
		if tenant is None:
			tenant = request.query.get("tenant")

		response = await self._send(message, tenant)
		return aiohttp.web.Response(text="{} replied with: {!r}\n".format(self.Target, response))


	async def receive(self, request, *, user_info):
		"""
		Receive a plaintext message and respond
		"""
		sender_app = user_info.get("azp")
		tenant = asab.contextvars.Tenant.get(None)
		text = await request.text()
		if tenant:
			print("Received message from {!r} in tenant {!r}: {!r}".format(sender_app, tenant, text))
			response = "Welcome to {}, {} appreciates your {!r}!".format(
				tenant, self.Name, text)
		else:
			print("Received message from {!r}: {!r}".format(sender_app, text))
			response = "Welcome, {} appreciates your {!r}!".format(
				self.Name, text)

		print("Sending response: {!r}".format(response))
		return aiohttp.web.Response(text=response)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
