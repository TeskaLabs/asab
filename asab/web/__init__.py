from ..abc import Module
from .container import WebContainer
from .websocket import WebSocketFactory
from .staticdir import StaticDirProvider


class Module(Module):

	def __init__(self, app):
		super().__init__(app)

		from .service import WebService
		self.service = WebService(app, "asab.WebService")


__all__ = (
	'WebContainer',
	'WebSocketFactory',
	'StaticDirProvider',
	'Module',
)
