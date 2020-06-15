import logging

from .service import ZooKeeperService

from ..abc.module import Module

#

L = logging.getLogger(__name__)

#


class Module(Module):

	def __init__(self, app, config_section="zookeeper"):
		super().__init__(app)
		self.Service = ZooKeeperService(app, "asab.ZooKeeperService", config_section)
