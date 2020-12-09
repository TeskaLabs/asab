import asab
import asab.web

from .service import ApiService


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		Module = asab.web.Module
		app.add_module(Module)

		self.Service = ApiService(app, "asab.ApiService")
