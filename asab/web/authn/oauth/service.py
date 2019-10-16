import asab

from .cache import OAuthIdentityCache
from .forwarder import OAuthForwarder


class OAuthClientService(asab.Service):
	"""
	OAuthClientService serves to provide methods and cache to oauthclient_middleware_factory
	and register OAuthForwarder, which serves to add forward endpoints to the provided web server container,
	so the client applications may get/post information about the OAuth login.
	"""

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.App = app
		self.MethodsDict = None
		self.IdentityCache = None
		self.Forwarder = None

	def add_oauth_methods(self, methods, identity_cache_longevity=60*60):
		self.MethodsDict = {}
		for method in methods:
			self.MethodsDict[method.Config["oauth_server_id"]] = method
		self.IdentityCache = OAuthIdentityCache(self.App, self.MethodsDict, identity_cache_longevity)

	def register_oauth_forwarder(self, container):
		if len(self.MethodsDict) == 0:
			raise RuntimeError("OAuth methods need to be specified first. Call 'add_oauth_methods' before registering forwarder.")
		self.Forwarder = OAuthForwarder(container=container, identity_cache=self.IdentityCache, methods_dict=self.MethodsDict)
