import asab

from .service import OpenIDConnectService


class Module(asab.Module):
	"""
	OAuth Client Module provides OAuthClientService and oauthclient_middleware_factory
	to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.
	"""

	def __init__(self, app):
		super().__init__(app)
		self.Service = OpenIDConnectService(app, "asab.OpenIDConnectService")


__all__ = (
	'OpenIDConnectService'
)
