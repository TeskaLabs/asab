import logging
import os

from ..abc.module import Module
from ..config import Config

from .service import DockerService

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'docker': {
			# Docker API or socket
			# Could be `http://myHost:2375` or `/var/run/docker.sock`
			'socket': '',
		}
	}
)


def running_in_docker():
	in_docker = os.path.exists('/.dockerenv') or os.path.isfile('/proc/self/cgroup')
	if in_docker:
		with open('/proc/self/cgroup', "r") as f:
			if not any('docker' in line for line in f.readlines()):
				in_docker = False
	return in_docker


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = DockerService(app, "asab.DockerService")
