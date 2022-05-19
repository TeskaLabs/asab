from ..abc import Module
from .websocket import WebSocketFactory
from .staticdir import StaticDirProvider


class Module(Module):

	def __init__(self, app):
		super().__init__(app)

		from .service import WebService
		self.service = WebService(app, "asab.WebService")


__all__ = (
	'WebSocketFactory',
	'StaticDirProvider',
	'Module',
)
