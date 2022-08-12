from .container import ZooKeeperContainer
from ..abc.module import Module


class Module(Module):

	def __init__(self, app):
		super().__init__(app)

		from .service import ZooKeeperService
		self.Service = ZooKeeperService(app, "asab.ZooKeeperService")


__all__ = [
	"ZooKeeperContainer",
	"Module",
]
