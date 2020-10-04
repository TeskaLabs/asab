import platform
import logging

import http.client
import json

from ..abc.service import Service
from ..config import Config

#

L = logging.getLogger(__name__)

#


class DockerService(Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)

	def load_hostname(self):
		hostname = platform.node()

		remote_api = Config.get("general", "docker_remote_api")

		if remote_api is not None and len(remote_api) != 0:
			# In docker, hostname defaults to container ID
			# It is necessary to use container name for better readability of the metrics
			try:
				if "https" in remote_api:
					conn = http.client.HTTPSConnection(remote_api.replace("https://", ""))
				else:
					conn = http.client.HTTPConnection(remote_api.replace("http://", ""))
				conn.request("GET", "/containers/{}/json".format(hostname))

				docker_info_request = conn.getresponse()
				if docker_info_request.status != 200:
					L.warning("Could not call the Docker remote API at '{}'. Is it enabled?".format(remote_api))
					return hostname
			except Exception as e:
				L.warning("Connection to Docker Remote API could not be established due to '{}'.".format(e))
				return hostname

			docker_info_data = docker_info_request.read()
			docker_info = json.loads(docker_info_data.decode("utf-8"))
			container_name = docker_info.get("Name")
			if container_name is None:
				L.warning("Docker Remote API does not provide container name. Using container ID as hostname.")
				return hostname

			# Store the container name in tags as host
			if container_name.startswith("/"):
				container_name = container_name[1:]
			return "{}{}".format(Config.get("general", "docker_name_prefix"), container_name)

		return hostname
