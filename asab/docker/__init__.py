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
		'asab:docker': {
			# Docker API or socket
			# Could be `http://myHost:2375` or `/var/run/docker.sock`
			'socket': '',
			'name_prefix': '',
		}
	}
)


def running_in_docker():
	return (
		os.path.exists('/.dockerenv') or (
			os.path.isfile('/proc/self/cgroup') and any('docker' in line for line in open('/proc/self/cgroup'))
		)
	)


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = DockerService(app, "asab.DockerService")
