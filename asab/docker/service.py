import socket
import platform
import logging
import os

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
			hostname = self.ContainerName
		else:
			L.warning("Failed to obtain docker container name from Docker API.")
		return hostname

	def load_servername(self):
		return self.ServerName

	def get_docker_info(self):
		container_id = get_docker_container_id()
		if container_id is None:
			L.warning("Failed to obtain docker container ID from cgroup.")
			return

		docker_info = call_docker_api(container_id)

		if docker_info is None:
			L.warning("Docker API does not provide container name. Using container ID as hostname.")
			self.ContainerName = container_id
			self.ServerName = self.App.HostName
			return

		container_name = docker_info.get("Name")
		self.ContainerName = container_name.lstrip("/")
		self.ServerName = docker_info.get("Config").get("Hostname")


def get_docker_container_id():
	if os.path.isfile('/proc/self/cgroup'):
		with open('/proc/self/cgroup', "r") as f:
			cgroup = f.read()
			if any('docker' in line for line in cgroup.split("\n")):
				container_id = cgroup.split("/docker/")[1].split("\n")[0]
				return container_id

	# since Ubuntu 22.04 linux kernel uses cgroups v2 which do not operate with /proc/self/cgroup file
	if os.path.isfile('/proc/self/mountinfo'):
		with open('/proc/self/mountinfo', "r") as f:
			for line in f.readlines():
				if '/docker/containers/' in line:
					container_id = line.split('/docker/containers/')[-1]
					container_id = container_id.split('/')[0]
					return container_id


def call_docker_api(container_id):
	remote_api = get_api_address_from_config()
	if len(remote_api) == 0:
		return
	if remote_api.startswith("https://"):
		conn = http.client.HTTPSConnection(remote_api.replace("https://", ""))
	elif remote_api.startswith("http://"):
		conn = http.client.HTTPConnection(remote_api.replace("http://", ""))
	else:
		conn = HTTPUnixConnection(remote_api)

	try:
		conn.request("GET", "http://localhost/containers/{}/json".format(container_id))

		docker_info = conn.getresponse()
		if docker_info.status != 200:
			L.warning(
				"Docker API call at '{}' failed.".format(remote_api),
				struct_data={'status': docker_info.status}
			)
			return

	except Exception as e:
		L.warning("Connection to Docker API could not be established: '{}'.".format(e))
		return

	docker_info_data = docker_info.read()
	docker_info = json.loads(docker_info_data.decode("utf-8"))

	return docker_info




def get_api_address_from_config():
	configsection = "docker"
	if configsection not in Config.sections():
		# Remove after Jun 2023
		if "asab:docker" in Config.sections():
			configsection = "asab:docker"
			L.warning("Using obsolete config section [asab:docker]. Preferred section name is [docker]")

	return Config.get(configsection, "socket")



class HTTPUnixConnection(http.client.HTTPConnection):
	'''
	This is limited-purpose HTTP client that runs on UNIX socket.
	It is meant only for communication with a Docker API.
	'''

	def connect(self):
		self.sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0, fileno=None)
		self.sock.connect(self.host)
