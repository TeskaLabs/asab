import re
import logging
import inspect

import asab
import aiohttp
import aiohttp.web
import yaml

import typing

from .doc_templates import SWAGGER_OAUTH_PAGE, SWAGGER_DOC_PAGE


##

L = logging.getLogger(__name__)

##


class DocWebHandler(object):
	def __init__(self, api_service, app, web_container, config_section_name="asab:doc"):
		self.App = app
		self.WebContainer = web_container
		self.WebContainer.WebApp.router.add_get("/doc", self.doc)
		self.WebContainer.WebApp.router.add_get(
			"/oauth2-redirect.html", self.oauth2_redirect
		)
		self.WebContainer.WebApp.router.add_get("/asab/v1/openapi", self.openapi)

		self.AuthorizationUrl = asab.Config.get(
			config_section_name, "authorizationUrl", fallback=None
		)
		self.TokenUrl = asab.Config.get(config_section_name, "tokenUrl", fallback=None)
		self.Scopes = asab.Config.get(config_section_name, "scopes", fallback=None)

		self.Manifest = api_service.Manifest


	def build_swagger_documentation(self) -> dict:
		"""Take a docstring of the class and a docstring of methods and merge them into Swagger data."""
		app_doc_string: str = self.App.__doc__
		app_description: str = get_description(app_doc_string)
		specification: dict = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(self.App.__class__.__name__),
				"description": app_description,
				"contact": {
					"name": "ASAB microservice",
					"url": "https://www.github.com/teskalabs/asab",
				},
				"version": "1.0.0",
			},
			"servers": [
				{"url": "/", "description": "Here"}
			],

			# Base path relative to openapi endpoint
			"paths": {},
			# Authorization
			# TODO: Authorization must not be always of OAuth type
			"components": {},
		}

		additional_info_dict: dict = self.get_additional_info(app_doc_string)
		if additional_info_dict is not None:
			specification.update(additional_info_dict)

		specification["components"]["securitySchemes"] = self.create_security_schemes()
		specification["info"]["version"] = self.get_manifest()
		specification["info"]["description"] = self.get_server_and_container_info(
			app_description
		)

		# routers sorting
		asab_routes = []
		microservice_routes = []

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == "HEAD":
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			path: str = self.get_path_from_route_info(route)

			if re.search("asab", path) or re.search("/doc", path) or re.search("/oauth2-redirect.html", path):
				asab_routes.append(self.parse_route_data(route))
			else:
				microservice_routes.append(self.parse_route_data(route))

		# add routers to 'paths' in order
		# TODO: sorting by tags alphabetically?

		for endpoint in microservice_routes:
			endpoint_name = list(endpoint.keys())[0]
			# if endpoint already exists, then update, else create a new one
			spec_endpoint = specification["paths"].get(endpoint_name)
			if spec_endpoint is None:
				spec_endpoint = specification["paths"][endpoint_name] = {}

			spec_endpoint.update(endpoint[endpoint_name])

		for endpoint in asab_routes:
			endpoint_name = list(endpoint.keys())[0]
			spec_endpoint = specification["paths"].get(endpoint_name)
			if spec_endpoint is None:
				spec_endpoint = specification["paths"][endpoint_name] = {}

			spec_endpoint.update(endpoint[endpoint_name])

		return specification

	def parse_route_data(self, route) -> dict:
		"""Take a route (a single endpoint with one method) and return its description data.

		---
		Example:

		>>> self.parse_route(myTestRoute)
		{
				'/my/endpoint': {
						'get': {
								'summary': 'This is a test route.',
								'description': 'This is a test route.\\n\\n\\nHandler: `MyBeautifulHandler.myTestRoute()`',
								'tags': ['myTag'],
								'responses': {'200': {'description': 'Success'}}
								}
						}
		}

		"""
		route_dict: dict = {}
		method_name: str = route.method.lower()
		route_path: str = self.get_path_from_route_info(route)

		parameters: list = extract_parameters(route)
		doc_string: str = extract_docstring(route)
		add_dict: dict = self.get_additional_info(doc_string)
		handler_name: str = extract_handler_name(route)
		class_name: str = extract_class_name(route)
		module_name: str = extract_module_name(route)
		method_dict: dict = extract_method_dict(route)
		method_dict.update(
			self.add_methods(doc_string, add_dict, handler_name, class_name, module_name, parameters)
		)

		path_object = route_dict.get(route_path)
		if path_object is None:
			route_dict[route_path] = path_object = {}
		path_object[method_name] = method_dict

		return route_dict


	def get_additional_info(self, docstring: typing.Optional[str]) -> typing.Optional[dict]:
		"""Take the docstring of a function and return additional data if they exist."""

		additional_info_dict: typing.Optional[dict] = None

		if docstring is not None:
			docstring = inspect.cleandoc(docstring)
			dashes_index = docstring.find("\n---\n")
			if dashes_index >= 0:
				try:
					additional_info_dict = yaml.load(
						docstring[dashes_index:], Loader=yaml.SafeLoader
					)  # everything after --- goes to add_dict
				except yaml.YAMLError as e:
					L.error(
						"Failed to parse '{}' doc string {}".format(
							self.App.__class__.__name__, e
						))
		L.warning("additional info dict: {}".format(additional_info_dict))
		return additional_info_dict

	def create_security_schemes(self) -> dict:
		"""Create security schemes if self.tokenUrl, self.authorizationUrl and self.Scopes exist."""
		security_schemes_dict = {}
		if self.AuthorizationUrl and self.TokenUrl:
			security_schemes_dict = {
				"oAuth": {
					"type": "oauth2",
					"description": "",
					"flows": {
						"authorizationCode": {
							"authorizationUrl": self.AuthorizationUrl,  # "http://localhost/seacat/api/openidconnect/authorize"
							"tokenUrl": self.TokenUrl,  # "http://localhost/seacat/api/openidconnect/token"
							"scopes": {
								"openid": "Required Scope for OpenIDConnect!",
							},
						}
					},
				}
			}
			if self.Scopes:
				for scope in self.Scopes.split(","):
					security_schemes_dict["oAuth"]["flows"][
						"authorizationCode"
					]["scopes"].update(
						{"scope": "{} scope.".format(scope.strip().capitalize())}
					)
		return security_schemes_dict

	def get_manifest(self) -> dict:
		"""Get version from MANIFEST.json if exists."""
		version = {}
		if self.Manifest:
			version = self.Manifest["version"]
		return version

	def get_server_and_container_info(self, description) -> str:
		"""Return info on which server and web container the user operates into description."""
		return "Running on: <strong>{}</strong> on: <strong>{}</strong>".format(
			self.App.ServerName, self.WebContainer.Addresses
		) + "<p>{}</p>".format(description)

	def get_path_from_route_info(self, route) -> str:
		"""Take a route and return its path."""
		route_info = route.get_info()
		if "path" in route_info:
			path = route_info["path"]
		elif "formatter" in route_info:
			path = route_info["formatter"]
		else:
			L.warning("Cannot obtain path info from route", struct_data=self.route_info)
		return path

	def add_methods(
		self,
		docstring: typing.Optional[str],
		add_dict: typing.Optional[dict],
		handler_name: str,
		class_name: str,
		module_name: str,
		parameters: list,
	):

		description: str = get_description(docstring)
		description += "\n\nHandler: `{}`".format(handler_name)

		new_methods: dict = {
			"summary": description.split("\n")[0],
			"description": description,
			"responses": {"200": {"description": "Success"}},
		}

		default_tag: str = asab.Config["swagger"].get("default_tag")
		if default_tag == "general":
			new_methods["tags"] = ["general"]
		elif default_tag == "class_name":
			new_methods["tags"] = [class_name]
		elif default_tag == "module_name":
			new_methods["tags"] = [module_name]

		if len(parameters) > 0:
			new_methods["parameters"] = parameters

		if add_dict is not None:
			new_methods.update(add_dict)

		return new_methods

	# This is the web request handler
	async def doc(self, request):
		"""
		Access the API documentation using a browser.
		---
		tags: ['asab.doc']
		"""

		swagger_js_url: str = "https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"
		swagger_css_url: str = "https://unpkg.com/swagger-ui-dist@4/swagger-ui.css"

		doc_page = SWAGGER_DOC_PAGE.format(
			title=self.App.__class__.__name__,
			swagger_css_url=swagger_css_url,
			swagger_js_url=swagger_js_url,
			openapi_url="./asab/v1/openapi",
		)

		return aiohttp.web.Response(text=doc_page, content_type="text/html")

	def oauth2_redirect(self, request):
		"""
		Required for the authorization to work.
		---
		tags: ['asab.doc']
		"""

		return aiohttp.web.Response(text=SWAGGER_OAUTH_PAGE, content_type="text/html")

	async def openapi(self, request):
		"""
		Download OpenAPI (version 3) API documentation (aka Swagger) in YAML.
		---
		tags: ['asab.doc']
		externalDocs:
		description: OpenAPI Specification
		url: https://swagger.io/specification/

		"""
		return aiohttp.web.Response(
			text=(yaml.dump(self.build_swagger_documentation(), sort_keys=False)),
			content_type="text/yaml",
		)


def get_description(docstring: typing.Optional[str]) -> str:
		"""Take the docstring of a function and parse it into description. Omit everything that comes after '---'."""
		if docstring is not None:
			docstring = inspect.cleandoc(docstring)
			dashes_index = docstring.find(
				"\n---\n"
			)  # find the index of the first three dashes

			# everything before --- goes to description
			if dashes_index >= 0:
				description = docstring[:dashes_index]
			else:
				description = docstring
		else:
			description = ""
		return description


def extract_parameters(route) -> list:
	"""Take a single route and return its parameters.

	---
	Example:

	>>> extract_parameters(myTestRoute)
	[
			{'in': 'path', 'name': 'parameter1', 'required': True},
			{'in': 'path', 'name': 'parameter2', 'required': True}
	]
	"""
	parameters: list = []
	route_info = route.get_info()
	if "formatter" in route_info:
		path = route_info["formatter"]
		for params in re.findall(r'\{[^\}]+\}', path):
				parameters.append({
					'in': 'path',
					'name': params[1:-1],
					'required': True,
				})
	return parameters


def extract_handler_name(route) -> str:
	if inspect.ismethod(route.handler):
		handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
	else:
		handler_name = "{}()".format(route.handler.__qualname__)
	return handler_name


def extract_class_name(route) -> str:
	L.warning("{:<20}".format("xxx"))
	if inspect.ismethod(route.handler):
		class_name = str(route.handler.__self__.__class__.__name__)
	else:
		class_name = str(route.handler.__qualname__.split(".")[0])
	L.warning("class name: {}".format(class_name))
	L.warning("module name: {}".format(route.handler.__module__))
	return class_name


def extract_module_name(route) -> str:
	return str(route.handler.__module__)


def extract_docstring(route) -> str:
	return route.handler.__doc__


def extract_method_dict(route) -> dict:
		method_dict = {}
		try:
			json_schema = route.handler.__getattribute__("json_schema")
			method_dict["requestBody"] = {
				"content": {"application/json": {"schema": json_schema}},
			}
		except AttributeError:
			pass
		return method_dict
