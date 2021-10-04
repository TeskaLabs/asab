import asab

from .service import OpenIDConnectService


class Module(asab.Module):
	"""
	OpenIDConnect Module provides OpenIDConnectService which supplies the userinfo data provided by
	the authorization server.
	"""

	def __init__(self, app):
		super().__init__(app)
		self.Service = OpenIDConnectService(app, "asab.OpenIDConnectService")


__all__ = (
	'OpenIDConnectService'
)
