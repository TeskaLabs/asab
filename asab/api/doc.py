import re
import logging
import inspect

import asab
import aiohttp
import aiohttp.web
import yaml

import typing

from .doc_templates import SWAGGER_OAUTH_PAGE, SWAGGER_DOC_PAGE
from ..web.auth import noauth
from ..web.tenant import NO_TENANT_ROUTES


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
		NO_TENANT_ROUTES.update({"/doc", "/oauth2-redirect.html", "/asab/v1/openapi"})

		self.AuthorizationUrl = asab.Config.get(
			config_section_name, "authorization_url", fallback=None
		)
		self.TokenUrl = asab.Config.get(config_section_name, "token_url", fallback=None)
		self.Scopes = asab.Config.get(config_section_name, "scopes", fallback=None)

		self.Manifest = api_service.Manifest

		self.DefaultRouteTag: str = asab.Config.get("asab:doc", "default_route_tag")
		if self.DefaultRouteTag not in ["module_name", "class_name"]:
			raise ValueError(
				"Unknown default_route_tag: {}. Choose between options "
				"'module_name' and 'class_name'.".format(self.DefaultRouteTag))

		self.ServerUrls: str = asab.Config.get(config_section_name, "server_urls", fallback="/").strip().split("\n")


	def build_swagger_documentation(self, host) -> dict:
		"""
		Take a docstring of the class and a docstring of methods and merge them into Swagger data.
		"""
		specification: dict = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(self.App.__class__.__name__),
				"description": get_docstring_description(self.App.__doc__),
				"contact": {
					"name": "ASAB-based microservice",
					"url": "https://www.github.com/teskalabs/asab",
				},
				"version": self.get_version_from_manifest(),
			},
			"servers": [
				{"url": "http://{}".format(host)}
			],
			"components": {
				"securitySchemes": self.create_security_schemes()},

			# Base path relative to openapi endpoint
			"paths": {},
			# Authorization
			# TODO: Authorization must not be always of OAuth type
		}

		# Application specification
		specification.update(get_docstring_yaml(self.App))

		# Find asab and microservice routes, sort them alphabetically by the first tag
		asab_routes = []
		routes = []

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == "HEAD":
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			# Determine which routes are asab-based
			if re.search("(asab|doc|oauth2-redirect.html|bspump)", self.get_route_path(route)):
				asab_routes.append(self.parse_route_data(route))
			else:
				routes.append(self.parse_route_data(route))

		routes.sort(key=get_first_tag)

		for endpoint in routes:
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
		"""
		Take a route (a single method of an endpoint) and return its description data.
		"""
		# Parse docstring description and yaml data
		docstring_description = "{}\n\n**Handler:** `{}`".format(
			get_docstring_description(route.handler.__doc__),
			get_handler_name(route)
		)

		# Create route info dictionary
		route_data: dict = {
			"summary": docstring_description.split("\n", 1)[0],
			"description": docstring_description.split("\n", 1)[1],
			"responses": {"200": {"description": "Success."}},
			"parameters": [],
			"tags": []
		}

		# Update it with parsed YAML and add query parameters
		docstring_yaml: dict = get_docstring_yaml(route.handler)
		if docstring_yaml is not None:
			route_data.update(docstring_yaml)

		# Find all path parameters, add them if not specified in docstring.
		for path_parameter in get_path_parameters(route):
			if path_parameter.get("name") is not None:
				if path_parameter["name"] not in [r["name"] for r in route_data["parameters"]]:
					route_data["parameters"].append(path_parameter)

		# Add default tag if not specified in docstring yaml
		if len(route_data["tags"]) == 0:
			# Try to get the tags from class docstring
			class_tags = get_class_tags(route)
			if class_tags:
				route_data["tags"] = class_tags[:1]
			# Or generate tag from component name
			elif self.DefaultRouteTag == "class_name":
				route_data["tags"] = [get_class_name(route)]
			elif self.DefaultRouteTag == "module_name":
				route_data["tags"] = [get_module_name(route)]

		# Create the route dictionary
		route_path: str = self.get_route_path(route)
		method_name: str = route.method.lower()
		method_dict: dict = get_json_schema(route)
		method_dict.update(route_data)

		return {route_path: {method_name: method_dict}}


	def create_security_schemes(self) -> dict:
		"""
		Create security schemes.
		"""
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

	def get_version_from_manifest(self) -> str:
		"""
		Get version from MANIFEST.json if exists.
		"""
		if self.Manifest:
			version = self.Manifest["version"]
		else:
			version = "unknown"
		return version

	def get_route_path(self, route) -> str:
		"""
		Take a route and return its path.
		"""
		route_info = route.get_info()
		if "path" in route_info:
			path = route_info["path"]
		elif "formatter" in route_info:
			path = route_info["formatter"]
		else:
			L.warning("Cannot obtain path info from route:{}".format(route_info))
		return path


	@noauth
	# This is the web request handler
	async def doc(self, request):
		"""
		Access the API documentation using a browser.
		---
		tags: ['asab.doc']
		"""

		swagger_js_url: str = "https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"
		swagger_css_url: str = "https://unpkg.com/swagger-ui-dist@4/swagger-ui.css"

		base_url = request.headers.get('Host')

		doc_page = SWAGGER_DOC_PAGE.format(
			title=self.App.__class__.__name__,
			swagger_css_url=swagger_css_url,
			swagger_js_url=swagger_js_url,
			openapi_url="http://{}/asab/v1/openapi".format(base_url),
		)

		return aiohttp.web.Response(text=doc_page, content_type="text/html")


	@noauth
	async def oauth2_redirect(self, request):
		"""
		Required for the authorization to work.
		---
		tags: ['asab.doc']
		"""

		return aiohttp.web.Response(text=SWAGGER_OAUTH_PAGE, content_type="text/html")


	@noauth
	async def openapi(self, request):
		"""
		Download OpenAPI (version 3) API documentation (aka Swagger) in YAML.
		---
		tags: ['asab.doc']
		externalDocs:
			description: OpenAPI Specification
			url: https://swagger.io/specification/

		"""

		host = request.headers.get('Host')

		return aiohttp.web.Response(
			text=(yaml.dump(self.build_swagger_documentation(host=host), sort_keys=False)),
			content_type="text/yaml",
		)


def get_docstring_description(docstring: typing.Optional[str]) -> str:
	"""
	Take the docstring of a function and parse it into description. Omit everything that comes after '---'.
	"""
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


def get_path_parameters(route) -> list:
	"""
	Return path parameters of a route.
	"""
	parameters: list = []
	route_info = route.get_info()
	if "formatter" in route_info:
		path = route_info["formatter"]
		for params in re.findall(r'\{[^\}]+\}', path):
				parameters.append({
					"in": "path",
					"name": params[1:-1],
					"required": True,
					"schema": {"type": "string"},
				})
	return parameters


def get_handler_name(route) -> str:
	if inspect.ismethod(route.handler):
		handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
	else:
		handler_name = "{}()".format(route.handler.__qualname__)
	return handler_name


def get_class_name(route) -> str:
	if inspect.ismethod(route.handler):
		class_name = str(route.handler.__self__.__class__.__name__)
	else:
		class_name = str(route.handler.__qualname__.split(".")[0])
	return class_name


def get_class_tags(route) -> typing.Optional[list]:
	if not inspect.ismethod(route.handler):
		return None
	return get_docstring_yaml(route.handler.__self__.__class__).get("tags")


def get_module_name(route) -> str:
	return str(route.handler.__module__)


def get_json_schema(route) -> dict:
		method_dict = {}
		try:
			json_schema = route.handler.__getattribute__("json_schema")
			method_dict["requestBody"] = {
				"content": {"application/json": {"schema": json_schema}},
			}
		except AttributeError:
			pass
		return method_dict


def get_first_tag(route_data: dict) -> str:
	"""
	Get tag from route data. Used for sorting tags alphabetically.
	"""
	for endpoint in route_data.values():
		for method in endpoint.values():
			if method.get("tags"):
				return method.get("tags")[0].lower()


def get_docstring_yaml(component) -> dict:
	"""
	Inspect the docstring of a component for YAML data and parse it if there is any.
	"""
	docstring = component.__doc__
	parsed_yaml_docstring_dict = {}

	if docstring is not None:
		docstring = inspect.cleandoc(docstring)
		dashes_index = docstring.find("\n---\n")
		if dashes_index >= 0:
			try:
				parsed_yaml_docstring_dict = yaml.load(
					docstring[dashes_index:], Loader=yaml.SafeLoader
				)  # everything after --- goes to add_dict
			except yaml.YAMLError as e:
				L.error(
					"Failed to parse '{}' doc string {}".format(
						component.__qualname__, e
					))
	return parsed_yaml_docstring_dict
