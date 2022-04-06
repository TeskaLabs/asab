import logging
import time

import asab
import asab.web
import asab.web.rest

#

L = logging.getLogger(__name__)

#


class MyApplication(asab.Application):
	"""
	Use Prometheus to track and visualize ASAB metrics.
	Accepts requests on port 8089.
	To see data in Prometheus, add these lines into scrape_configs section in your prometheus.yml config file:
	scrape_configs:
	- job_name: 'metrics_animal_example'
			metrics_path: '/asab/v1/metrics'
			scrape_interval: 10s
			static_configs:
			- targets: ['127.0.0.1:8089']

	There is 60s lag in ASAB-Prometheus data transfer.
	Call the unicorn and see what happens!
	"""

	async def initialize(self):
		asab.Config.read_string(
			"""
[web]
listen=0.0.0.0 8089

[asab:metrics]
target=prometheus influxdb

[asab:metrics:influxdb]
url=http://localhost:8086
username=test
password=testtest
db=test

[asab:metrics:prometheus]
		"""
		)
		# Loading the web service module
		self.add_module(asab.web.Module)
		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, "web")

		# Create ApiService to enable asab/v1/metrics endpoint
		from asab.api import ApiService

		self.ApiService = ApiService(self)
		self.ApiService.initialize_web(container)

		container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		# Add a route
		container.WebApp.router.add_get("/racoon", self.get_racoon)
		container.WebApp.router.add_get("/unicorn", self.get_unicorn)
		container.WebApp.router.add_get("/jellyfish", self.get_jellyfish)
		container.WebApp.router.add_put("/dolphin", self.get_dolphin)

	async def get_racoon(self, request):
		message = "Hi, I am racoon."
		return asab.web.rest.json_response(request=request, data={"message": message})

	async def get_unicorn(self, request):
		message = "Hi, I am unicorn."
		return asab.web.rest.json_response(
			request=request, data={"message": message}, status=401
		)

	async def get_jellyfish(self, request):
		raise RuntimeError()


	@asab.web.rest.json_schema_handler(
		{
			"type": "object",
			"properties": {
				"name": {"type": "string"},
				"favourite_food": {"type": "string"},
			},
			"required": ["name", "favourite_food"]
		}
	)
	async def get_dolphin(self, request, *, json_data):
		message = "Hi, I am dolphin {} and I like {}!".format(json_data.get("name"), json_data.get("favourite_food"))
		time.sleep(0.05)
		return asab.web.rest.json_response(request=request, data={"message": message})


if __name__ == "__main__":
	app = MyApplication()
	app.run()
