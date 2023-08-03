import typing
import aiohttp.web

from ..abc import Module
from .container import WebContainer
from .websocket import WebSocketFactory
from .staticdir import StaticDirProvider


class Module(Module):
	"""
	Module for running and easy manipulation of the web server.
	"""

	def __init__(self, app):
		super().__init__(app)

		from .service import WebService
		self.service = WebService(app, "asab.WebService")


def create_web_server(app, section: str = "web", config: typing.Optional[dict] = None) -> aiohttp.web.UrlDispatcher:
	"""
	Build the web server with the specified configuration.

	It is an user convenience function that simplifies typical way of how the web server is created.

	Args:
		app (asab.Application): A reference to the ASAB Application.
		section (str): Configuration section name with which the WebContainer will be created.
		config (dict | None): Additional server configuration.

	Returns:
		[WebContainer Application Router object](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=router#router).

	Examples:

	```python
	class MyApplication(asab.Application):
		def __init__(self):
			super().__init__()
			web = asab.web.create_web_server(self)
			web.add_get('/hello', self.hello)

		async def hello(self, request):
			return asab.web.rest.json_response(request, data="Hello, world!\n")

	```
	"""
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
