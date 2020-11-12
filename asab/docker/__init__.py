import logging

from ..abc.module import Module
from ..config import Config

from .service import DockerService

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'general': {
			# Used for detection of container name,
			# example: /var/run/docker.sock
			'docker_socket': '',
			'docker_name_prefix': '',
		}
	}
)


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = DockerService(app, "asab.DockerService")
