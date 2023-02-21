import unittest
import logging

from asab.api.doc import DocWebHandler

L = logging.getLogger(__name__)


class TestDocWebHandler(unittest.TestCase):
	def setUp(self) -> None:
		super().setUp()
		self.App = App()
		self.test_app = App()
		self.test_api_service = ServiceWithManifest()
		self.test_web_container = WebContainer()
		self.AuthorizationUrl = "AuthorizationUrl"
		self.TokenUrl = "TokenUrl"
		self.Scopes = "Scopes"
		self.Manifest = ""
		self.handlerObject = DocWebHandler(self.test_api_service, self.test_app, self.test_web_container)

		# in order to access 'self.WebContainer.WebApp.router.routes()', we have to mock these classes below
		self.WebContainer = WebContainer()


class ServiceWithManifest:
	def __init__(self) -> None:
		self.Manifest = None


class App:
	def __init__(self) -> None:
		self.__doc__ = "This is a test app for TestDocWebHandler."
		self.__class__.__name__ = "TestApp"
		self.ServerName = "ServerName"



class WebContainer:
	def __init__(self) -> None:
		self.WebApp = WebApp()
		self.Addresses = []


class WebApp:
	def __init__(self) -> None:
		self.router = router()


class router:
	def __init__(self) -> None:
		pass

	def routes(self):
		mocked_router_list = []
		mocked_router_list.append(MockedRouterObject("path/to/file", "PUT"))
		mocked_router_list.append(MockedRouterObject("path/to/file", "GET"))
		mocked_router_list.append(MockedRouterObject("another/path", "GET"))
		mocked_router_list.append(MockedRouterObject("another/path", "DELETE"))

		return mocked_router_list

	def add_get(endpoint, function, neco):
		pass


class MockedRouterObject():
	def __init__(self, endpoint_name: str, http_method: str, ) -> None:
		self.method = http_method
		self.endpoint = endpoint_name

	def get_info(self) -> dict[str]:
		return {
			"path": self.endpoint,
		}

	def handler(self) -> None:
		"""This is a test handler.

		Returns:
			nothing special
		---
		tags: [test_handler]
		"""
		return None

# TODO: route_info v route generuje slovník, ve kterém je buďto 'path' anebo 'formatter' - mám použít nějaké randomizování při mockování do unit testu

# TODO: vymyslet, jaké unit testy by se daly pro tu funkci napsat
# MOŽNÁ: vygenerovat template pro swagger a pak se ptát, jestli obsahuje správné slovníky
