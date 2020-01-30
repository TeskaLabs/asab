import asab

from .middleware import oauthclient_middleware_factory
from .method import ABCOAuthMethod
from .method import GitHubOAuthMethod
from .method import OpenIDConnectMethod

from .service import OAuthClientService


class Module(asab.Module):
	'''
	OAuth Client Module provides OAuthClientService and oauthclient_middleware_factory
	to connect with the user info endpoint of OAuth 2.0 server to obtain identity of the user
	associated with the provided access token.
	'''

	def __init__(self, app):
		super().__init__(app)
		self.Service = OAuthClientService(app, "asab.OAuthClientService")


__all__ = (
	'oauthclient_middleware_factory',
	'ABCOAuthMethod',
	'GitHubOAuthMethod',
	'OpenIDConnectMethod',
	'OAuthClientService',
)
