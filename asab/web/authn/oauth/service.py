import asab
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
		self.Methods = {}
		self.DefaultMethod = None
		self.Forwarder = None

		self.UserInfoCache = {}
		self.UserInfoCacheLongevity = 60  # In seconds

		app.PubSub.subscribe("Application.tick/60!", self.on_tick60)


	def append_method(self, method):
		self.Methods[method.Config["oauth_server_id"]] = method
		if self.DefaultMethod is None:
			self.DefaultMethod = method
		if self.Forwarder is not None:
			self.Forwarder.Methods = self.Methods


	def get_method(self, oauth_server_id):
		if oauth_server_id is None:
			return self.DefaultMethod
		return self.Methods[oauth_server_id]


	def configure(self, container, configure_forwarder=True, configure_middleware=True):
		"""
		Configure method configured OAuthForwarder and oauthclient_middleware to obtain information about OAuth
		identity and thus restrict access to the content.

		OAuthForwarderserves to add forward endpoints to the provided web server container,
		so the client applications may get/post information about the OAuth login.

		:param container: container which would be configured
		:param configure_forwarder: flag which specifies if to configure OAuthForwarder
		:param configure_middleware: flag which specifies if to configure oauthclient_middleware
		:return:
		"""

		if len(self.Methods) == 0:
			raise RuntimeError("OAuth methods need to be specified first. Call 'add_oauth_methods' before registering forwarder.")

		if configure_forwarder is True:
			self.Forwarder = OAuthForwarder(container=container, service=self)

		if configure_middleware is True:
			container.WebApp.middlewares.append(
				asab.web.authn.authn_middleware_factory(
					self.App,
					"oauth2client",
					oauth_client_service=self,
				)
			)


	def on_tick60(self, event_name):
		keys_to_remove = set()
		for key, (_, _, expired_at) in self.UserInfoCache.items():
			if expired_at < self.App.Loop.time():
				keys_to_remove.add(key)

		for key in keys_to_remove:
			del self.UserInfoCache[key]
