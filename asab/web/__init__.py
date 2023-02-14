from ..abc import Module
from .container import WebContainer
from .websocket import WebSocketFactory
from .staticdir import StaticDirProvider


class Module(Module):

	def __init__(self, app):
		super().__init__(app)

		from .service import WebService
		self.service = WebService(app, "asab.WebService")


def create_web_server(app, section="web", config=None):
	'''
	Build a web server.

	It is an user convenience fucntion that simplifies typical way of how the web server is created.
	'''
	app.add_module(Module)
	websvc = app.get_service("asab.WebService")
	container = WebContainer(websvc, section, config=config)
	return container.WebApp.router


__all__ = (
	'WebContainer',
	'WebSocketFactory',
	'StaticDirProvider',
	'Module',
)
