import asab

from .service import WebService
from .websocket import WebSocketFactory
from .staticdir import StaticDirProvider
from .container import WebContainer


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = WebService(app, "asab.WebService")


__all__ = (
	'WebService',
	'WebSocketFactory',
	'StaticDirProvider',
	'WebContainer',
	'Module',
)
