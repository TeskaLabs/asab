#!/usr/bin/env python3
import logging
import typing
import secrets
import asab.web.rest
import asab.web.auth
import asab.web.tenant
import asab.contextvars
import asab.exceptions

if "web" not in asab.Config:
	asab.Config["web"] = {
		# Set up a web container listening at port 8080
		"listen": "8080"
	}

if "tenants" not in asab.Config:
	asab.Config["tenants"] = {
		# Define known tenants
		"ids": "default brothers-workspace big-corporation"
	}

if "auth" not in asab.Config:
	asab.Config["auth"] = {
		# Enable all authentication and authorization, or switch into MOCK mode.
		"enabled": "mock",  # Mock authorization, useful for debugging.
		# "enabled": "yes",   # Authorization is enabled (default).

		# Activating the mock mode disables communication with the authorization server.
		# The requests' Authorization headers are ignored and AuthService provides mock authorization with mock user info.
		# You can provide custom user info by specifying the path pointing to your JSON file.
		"mock_user_info_path": "./mock-userinfo.json",

		# In mock mode, it is possible to configure URL for direct access token intropspection.
		# "introspection_url": "http://localhost:8900/nginx/introspect/openidconnect",

		# URL of the authorization server's JWK public keys, used for ID token verification.
		# This option is ignored in mock mode or when authorization is disabled.
		# "public_keys_url": "http://localhost:3081/.well-known/jwks.json",
	}


class NotesApplication(asab.Application):
	"""
	Web application with a simple CRUD REST API for notes management.
	Demonstrates the usage of the authorization module (asab.web.auth).
	"""

	def __init__(self):
		super().__init__()

		# Initialize web container
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(self.WebService, "web")

		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		from asab.api import ApiService
		self.ApiService = ApiService(self)
		self.ApiService.initialize_web(self.WebContainer)

		# Initialize multitenancy and authorization
		self.TenantService = asab.web.tenant.TenantService(self)
		self.AuthService = asab.web.auth.AuthService(self)

		# Add routes
		self.WebContainer.WebApp.router.add_get("/", self.info)
		self.WebContainer.WebApp.router.add_get("/{tenant}/note", self.list_notes)
		self.WebContainer.WebApp.router.add_post("/{tenant}/note", self.create_note)
		self.WebContainer.WebApp.router.add_get("/{tenant}/note/{note_id}", self.read_note)
		self.WebContainer.WebApp.router.add_put("/{tenant}/note/{note_id}", self.edit_note)
		self.WebContainer.WebApp.router.add_delete("/{tenant}/note/{note_id}", self.delete_note)

		# Notes storage
		self.Notes: typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]] = {
			# Add a few notes so that the storage is not empty
			"default": {  # Tenant ID
				"12345678": {  # Note ID
					"_id": "12345678",
					"created_by": "that-one-developer:)",
					"content": "This is an example note in tenant 'default'!",
				}
			},
			"brothers-workspace": {
				"abcdefgh": {
					"_id": "abcdefgh",
					"created_by": "that-one-developer:)",
					"content": "This is another example note, this time in tenant 'brothers-workspace'!",
				}
			},
		}


	# Disable authentication and authorization for this endpoint
	@asab.web.auth.noauth
	# Do not require tenant parameter in URL (asab.contextvars.Tenant defaults to None)
	@asab.web.tenant.allow_no_tenant
	async def info(self, request):
		"""
		Show application info.

		No authentication or authorization required, but also no user details are available.
		"""
		data = {
			"message": "This app stores notes. Call GET /note to see stored notes.",
		}
		return asab.web.rest.json_response(request, data)


	async def list_notes(self, request):
		"""
		Show notes stored in the current tenant.

		Authentication required.
		"""
		tenant = asab.contextvars.Tenant.get()
		authz = asab.contextvars.Authz.get()

		notes = self.Notes.get(tenant, {})
		data = {
			"count": len(notes),  # Anybody can see how many notes are there
		}
		if authz.has_resource_access("note:read"):
			# Seeing the actual notes requires authorized access to "note:read"
			data["data"] = notes

		return asab.web.rest.json_response(request, data)


	@asab.web.auth.require("note:read")
	async def read_note(self, request):
		"""
		Find note by ID in the current tenant and return it.

		Authentication and authorization of "note:read" required.
		"""
		tenant = asab.contextvars.Tenant.get()

		note_id = request.match_info["note_id"]
		if tenant in self.Notes and note_id in self.Notes[tenant]:
			return asab.web.rest.json_response(request, self.Notes[tenant][note_id])
		else:
			return asab.web.rest.json_response(request, {"result": "NOT-FOUND"}, status=404)


	@asab.web.rest.json_schema_handler(
		{"type": "string"}
	)
	@asab.web.auth.require("note:edit")
	async def create_note(self, request, *, json_data):
		"""
		Create a note in the current tenant.

		Authentication and authorization of "note:edit" required.
		"""
		tenant = asab.contextvars.Tenant.get()
		authz = asab.contextvars.Authz.get()

		if tenant not in self.Notes:
			self.Notes[tenant] = {}
		note_id = secrets.token_urlsafe(8)
		self.Notes[tenant][note_id] = {
			"_id": note_id,
			"created_by": authz.CredentialsId,
			"content": json_data,
		}
		return asab.web.rest.json_response(request, {"_id": note_id}, status=201)


	@asab.web.rest.json_schema_handler(
		{"type": "string"}
	)
	@asab.web.auth.require("note:edit")
	async def edit_note(self, request, *, json_data):
		"""
		Update an existing note in the current tenant.

		Authentication and authorization of "note:edit" required.
		"""
		tenant = asab.contextvars.Tenant.get()

		note_id = request.match_info["note_id"]
		if tenant in self.Notes and note_id in self.Notes[tenant]:
			self.Notes[tenant][note_id]["content"] = json_data
			return asab.web.rest.json_response(request, {"result": "OK"})
		else:
			return asab.web.rest.json_response(request, {"result": "NOT-FOUND"}, status=404)


	@asab.web.auth.require("note:delete")
	async def delete_note(self, request):
		"""
		Find note by ID in the current tenant and delete it.

		Authentication and authorization of "note:delete" required.
		"""
		tenant = asab.contextvars.Tenant.get()

		note_id = request.match_info["note_id"]
		if tenant in self.Notes and note_id in self.Notes[tenant]:
			del self.Notes[tenant][note_id]
			return asab.web.rest.json_response(request, {"result": "OK"})
		else:
			return asab.web.rest.json_response(request, {"result": "NOT-FOUND"}, status=404)


if __name__ == "__main__":
	app = NotesApplication()
	app.run()
