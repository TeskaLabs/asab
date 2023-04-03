#!/usr/bin/env python3
import asab.web.rest
import asab.web.authz
import typing

asab.Config.add_defaults({
	"web": {
		"authorization": True
	}
})



class MyApplication(asab.Application):
	"""
	7 possible variants:
	- no tenant, no auth
	- no tenant, authentication
	- no tenant, authentication, resource authorization
	- tenant in path, authentication, tenant authorization
	- tenant in path, authentication, tenant authorization, resource authorization
	- tenant in query, authentication, tenant authorization
	- tenant in query, authentication, tenant authorization, resource authorization
	"""

	def __init__(self):
		super().__init__()

		self.add_module(asab.web.Module)

		# Locate the web service
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")


		self.AuthzService = asab.web.authz.AuthzService(self)
		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
		self.WebContainer.WebApp.middlewares.append(asab.web.authz.auth_middleware_factory(self.AuthzService))

		# Add a route to the handler method
		self.WebContainer.WebApp.router.add_get("/no_auth", self.simple)
		self.WebContainer.WebApp.router.add_get("/auth", self.auth)  # equivalent to "/optional_tenant"
		self.WebContainer.WebApp.router.add_get("/auth/resource_check", self.auth_resource)  # equivalent to "/optional_tenant/resource_check"
		self.WebContainer.WebApp.router.add_get("/{tenant}/obligatory_tenant", self.tenant_in_path)
		self.WebContainer.WebApp.router.add_get("/{tenant}/obligatory_tenant/resource_check", self.tenant_in_path_resources)
		self.WebContainer.WebApp.router.add_get("/optional_tenant", self.tenant_in_query)
		self.WebContainer.WebApp.router.add_get("/optional_tenant/resource_check", self.tenant_in_query_resources)


	@asab.web.authz.no_auth
	async def simple(self, request):
		"""
		NO AUTH
		- authentication skipped

		- `tenant`, `user_info`, `resources` params not allowed
		"""
		data = {
			"tenant": "NOT ALLOWED",
			"resources": "NOT ALLOWED",
			"user_info": "NOT ALLOWED",
		}
		return asab.web.rest.json_response(request, data)


	# async def auth(self, request):  # MINIMAL
	async def auth(self, request, *, tenant: None, user_info: dict, resources: frozenset):
		"""
		AUTH
		- returns 401 if authentication not successful

		- `user_info`, `resources` params allowed
		- `tenant` param allowed, but is always None
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth(self, request):  # MINIMAL
	async def auth_resource(self, request, *, tenant: None, user_info: dict, resources: frozenset):
		"""
		AUTH + RESOURCE CHECK
		- returns 401 if authentication not successful
		- globally granted resources checked
		- returns 403 if resources not granted

		- `user_info`, `resources` params allowed
		- `tenant` param allowed, but is always None
		- `resources` contain only globally granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_path(self, request, *, tenant: str, user_info: dict, resources: frozenset):
		"""
		AUTH + OBLIGATORY TENANT
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 403 if tenant not accessible

		- `user_info`, `resources` params allowed
		- `tenant` param required, cannot be None
		- `resources` contain tenant-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_query(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		AUTH + OPTIONAL TENANT
		- returns 401 if authentication not successful
		- `tenant` access checked IF "tenant" IN QUERY
		- returns 403 if tenant in query and not accessible

		- `user_info`, `resources` params allowed
		- `tenant` param required, can be None
		- `resources` contain tenant-granted resources if tenant in query,
			otherwise globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_path_resources(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		AUTH + OBLIGATORY TENANT + RESOURCE CHECK
		- returns 401 if authentication not successful
		- `tenant` access checked
		- returns 403 if tenant not accessible
		- tenant-accessible resources checked
		- returns 403 if resources not granted

		- `user_info`, `resources` params allowed
		- `tenant` param required, cannot be None
		- `resources` contain only resources granted within tenant
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


	@asab.web.authz.require("something:access", "something:edit")
	# async def auth(self, request, *, tenant):  # MINIMAL
	async def tenant_in_query_resources(self, request, *, tenant: typing.Union[str|None], user_info: dict, resources: frozenset):
		"""
		AUTH + OPTIONAL TENANT + RESOURCE CHECK
		- returns 401 if authentication not successful
		- `tenant` access checked IF "tenant" IN QUERY
		- returns 403 if tenant in query AND not accessible
		- tenant-accessible resources checked if tenant specified,
			otherwise globally-accessible resources checked
		- returns 403 if resources not granted

		- `user_info`, `resources` params allowed
		- `tenant` param required, can be None
		- `resources` contain tenant-granted resources if tenant in query,
			otherwise globally-granted resources
		"""
		data = {
			"tenant": tenant,
			"resources": list(resources),
			"user_info": user_info,
		}
		return asab.web.rest.json_response(request, data)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
