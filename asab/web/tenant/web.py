from .. import rest


class TenantWebHandler(object):

	def __init__(self, app, svc, web_container):

		self.TenantService = svc

		web_app = web_container.WebApp

		web_app.router.add_get('/tenants', self.get_tenants)

	async def get_tenants(self, request):

		tenants = self.TenantService.get_tenants()

		return rest.json_response(request, data=tenants)
