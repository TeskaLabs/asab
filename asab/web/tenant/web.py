from .. import rest


class TenantWebHandler(object):

	def __init__(self, app, svc):

		self.TenantService = svc

		web_app = app.WebContainer.WebApp

		web_app.router.add_get('/tenants', self.get_list_of_tenants)

	async def get_list_of_tenants(self, request):

		tenants = self.TenantService.get_list_of_tenants()

		return rest.json_response(request, data=tenants)
