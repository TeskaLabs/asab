from .service import ZooKeeperService
from ..abc.module import Module
from .container import ZooKeeperContainer
from .builder import KazooWrapper
__all__ = [
	"ZooKeeperContainer",
	"KazooWrapper",
]


class Module(Module):

	def __init__(self, app):
		super().__init__(app)
		self.Service = ZooKeeperService(app, "asab.ZooKeeperService")
