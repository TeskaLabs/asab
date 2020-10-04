from .service import ZooKeeperService
from ..abc.module import Module


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = ZooKeeperService(app, "asab.ZooKeeperService")
