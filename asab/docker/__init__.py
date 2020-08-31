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
			# see: https://medium.com/@ssmak/how-to-enable-docker-remote-api-on-docker-host-7b73bd3278c6
			# example: http://myHost:2375
			'docker_remote_api': '',
			'docker_name_prefix': '',
		}
	}
)


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = DockerService(app, "asab.DockerService")
