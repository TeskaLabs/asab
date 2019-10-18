import asab

from .cache import OAuthIdentityCache
from .forwarder import OAuthForwarder


class OAuthClientService(asab.Service):
	"""
	OAuthClientService serves to provide methods and cache to oauthclient_middleware_factory
	and register OAuthForwarder, which serves to add forward endpoints to the provided web server container,
	so the client applications may get/post information about the OAuth login.
	"""

	asab.Config.add_defaults({
		"OAuthClientService": {
			"identity_cache_longevity": 60*60,
		}
	})

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.App = app
		self.MethodsDict = {}
		self.IdentityCache = OAuthIdentityCache(self.App, self.MethodsDict, int(asab.Config["OAuthClientService"]["identity_cache_longevity"]))
		self.Forwarder = None

	def append_method(self, method):
		self.MethodsDict[method.Config["oauth_server_id"]] = method
		self.IdentityCache.MethodsDict = self.MethodsDict
		if self.Forwarder is not None:
			self.Forwarder.MethodsDict = self.MethodsDict

	def configure(self, container):
		if len(self.MethodsDict) == 0:
			raise RuntimeError("OAuth methods need to be specified first. Call 'add_oauth_methods' before registering forwarder.")
		self.Forwarder = OAuthForwarder(container=container, identity_cache=self.IdentityCache, methods_dict=self.MethodsDict)
