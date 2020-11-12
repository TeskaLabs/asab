import platform
import logging

import socket

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

		docker_socket = Config.get("general", "docker_socket")

		if docker_socket is not None and len(docker_socket) != 0:

			# In docker, hostname defaults to container ID
			# It is necessary to use container name for better readability of the metrics
			try:
				sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				sock.connect(docker_socket)
				sock.sendall(
					"GET /v1.19/containers/{}/json HTTP/1.1\r\nHost: /var/run/docker.sock\r\n\r\n".format(
						hostname
					).encode("utf-8")
				)

				socket_response = ""
				sock.settimeout(5.0)
				while "\n0" not in socket_response:
					socket_response += sock.recv(1024).decode("utf-8")

				# Extract the name
				name_split = socket_response.split("\"Name\":\"")
				if len(name_split) > 1:
					name = name_split[1].split("\"")[0].replace("/", "")

					# Store the container name in tags as host
					return "{}{}".format(Config.get("general", "docker_name_prefix"), name)

			except Exception as e:
				L.warning("Connection to Docker Remote API could not be established due to '{}'.".format(e))
				return hostname

		L.warning("Docker Socket does not provide container name. Using container ID as hostname.")
		return hostname
