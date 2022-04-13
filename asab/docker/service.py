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
		self.ContainerName = None
		self.ServerName = None
		self.get_docker_info()

	def load_hostname(self):
		hostname = platform.node()
		if self.ContainerName is not None:
			hostname = "{}{}".format(Config.get("asab:docker", "name_prefix"), self.ContainerName)
		else:
			L.warning("Failed to obtain docker container name from Docker API.")
		return hostname

	def load_servername(self):
		return self.ServerName

	def get_docker_info(self):
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

				# TODO: Make more elegant
				with open("/proc/self/cgroup", "r") as cgroup_file:
					cgroup = cgroup_file.read()
				conn.request("GET", "http://localhost/containers/{}/json".format(
					cgroup.split("/docker/")[1].split("\n")[0]
				))

				docker_info_request = conn.getresponse()
				if docker_info_request.status != 200:
					L.warning(
						"Docker API call at '{}' failed.".format(remote_api),
						struct_data={'status': docker_info_request.status}
					)
					return

			except Exception as e:
				L.warning("Connection to Docker API could not be established: '{}'.".format(e))
				return

			docker_info_data = docker_info_request.read()
			docker_info = json.loads(docker_info_data.decode("utf-8"))
			container_name = docker_info.get("Name")
			if container_name is None:
				L.warning("Docker API does not provide container name. Using container ID as hostname.")
				return

			# Store the container name in tags as host
			if container_name.startswith("/"):
				self.ContainerName = container_name[1:]

			# ServerName is also good to know
			self.ServerName = docker_info.get("Config").get("Hostname")



class HTTPUnixConnection(http.client.HTTPConnection):
	'''
	This is limited-purpose HTTP client that runs on UNIX socket.
	It is meant only for communication with a Docker API.
	'''

	def connect(self):
		self.sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0, fileno=None)
		self.sock.connect(self.host)
