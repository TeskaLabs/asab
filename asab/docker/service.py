import socket
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

		remote_api = Config.get("asab:docker", "socket")
		if len(remote_api) > 0:
			# In docker, hostname defaults to container ID
			# It is necessary to use container name for better readability of the metrics
			try:

				if remote_api.startswith("https://"):
					conn = http.client.HTTPSConnection(remote_api.replace("https://", ""))
				elif remote_api.startswith("http://"):
					conn = http.client.HTTPConnection(remote_api.replace("http://", ""))
				else:
					conn = HTTPUnixConnection(remote_api)

				conn.request("GET", "/containers/{}/json".format(hostname))

				docker_info_request = conn.getresponse()
				if docker_info_request.status != 200:
					L.warning(
						"Docker API call at '{}' failed.".format(remote_api),
						struct_data={'status': docker_info_request.status}
					)
					return hostname

			except Exception as e:
				L.warning("Connection to Docker API could not be established: '{}'.".format(e))
				return hostname

			docker_info_data = docker_info_request.read()
			docker_info = json.loads(docker_info_data.decode("utf-8"))
			container_name = docker_info.get("Name")
			if container_name is None:
				L.warning("Docker API does not provide container name. Using container ID as hostname.")
				return hostname

			# Store the container name in tags as host
			if container_name.startswith("/"):
				container_name = container_name[1:]
			return "{}{}".format(Config.get("asab:docker", "name_prefix"), container_name)


		L.warning("Failed to obtain docker container name from Docker API.")
		return hostname


class HTTPUnixConnection(http.client.HTTPConnection):
	'''
	This is limited-purpose HTTP client that runs on UNIX socket.
	It is meant only for communication with a Docker API.
	'''

	def connect(self):
		self.sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0, fileno=None)
		self.sock.connect(self.host)
