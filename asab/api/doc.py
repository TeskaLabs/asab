import re
import logging
import inspect

import asab
import aiohttp
import aiohttp.web
import yaml

##

L = logging.getLogger(__name__)


##


class DocWebHandler(object):

	def __init__(self, api_service, app, web_container, config_section_name='asab:doc'):
		self.App = app
		self.WebContainer = web_container
		self.WebContainer.WebApp.router.add_get('/doc', self.doc)
		self.WebContainer.WebApp.router.add_get('/oauth2-redirect.html', self.oauth2_redirect)
		self.WebContainer.WebApp.router.add_get('/asab/v1/openapi', self.openapi)

		self.AuthorizationUrl = asab.Config.get(config_section_name, "authorizationUrl", fallback=None)
		self.TokenUrl = asab.Config.get(config_section_name, "tokenUrl", fallback=None)
		self.Scopes = asab.Config.get(config_section_name, "scopes", fallback=None)

		self.Manifest = api_service.Manifest


	def build_swagger_specs(self):
		"""
		Takes a docstring of a class and a docstring of methods and merges them
		into a Swagger specification.
		"""

		doc_str = self.App.__doc__
		add_dict = None

		if doc_str is not None:
			doc_str = inspect.cleandoc(doc_str)
			i = doc_str.find("\n---\n")
			if i >= 0:
				self.description = doc_str[:i]
				try:
					add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
				except yaml.YAMLError as e:
					L.error("Failed to parse '{}' doc string {}".format(self.App.__class__.__name__, e))
			else:
				self.description = doc_str
		else:
			self.description = ""

		specs = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(self.App.__class__.__name__),
				"description": self.description,
				"contact": {
					"name": "ASAB microservice",
					"url": "https://www.github.com/teskalabs/asab",
				},
				"version": "1.0.0"
			},
			"servers": [{"url": "../../"}],  # Base path relative to openapi endpoint
			"paths": {},

			# Authorization
			# TODO: Authorization must not be always of OAuth type
			"components": {},
		}

		# Get rid of securitySchemes if there is no authorizationUrl or tokenUrl
		if self.AuthorizationUrl and self.TokenUrl:
			specs["components"].update({
				"securitySchemes": {
					"oAuth": {
						"type": "oauth2",
						"description": "",
						"flows": {
							"authorizationCode": {
								"authorizationUrl": self.AuthorizationUrl,  # "http://localhost/seacat/api/openidconnect/authorize"
								"tokenUrl": self.TokenUrl,  # "http://localhost/seacat/api/openidconnect/token"
								"scopes": {
									"openid": "Required Scope for OpenIDConnect!",
								}
							}
						}
					}
				},
			})

		# Gets all the scopes from config and puts them into scopes
		if self.Scopes and self.AuthorizationUrl and self.TokenUrl:
			for scope in self.Scopes.split(","):
				specs["components"]["securitySchemes"]["oAuth"]["flows"]["authorizationCode"]["scopes"].update({scope: "{} scope.".format(scope.strip().capitalize())})

		# Version from MANIFEST.json
		if self.Manifest:
			specs["info"]["version"] = self.Manifest["version"]

		# Show what server/docker container you are on, and it's IP
		specs["info"]["description"] = ("Running on: <strong>{}</strong> on: <strong>{}</strong>".format(
			self.App.ServerName, self.WebContainer.Addresses) + "<p>{}</p>".format(self.description))
		# specs["servers"].append({"url": "http://{}:{}".format(server[0], server[1])})

		if add_dict is not None:
			specs.update(add_dict)


		asab_routers = []
		service_routers = []
		doc_routers = []

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			if re.search("/doc", path) or re.search("/oauth-redirect.html", path):
				doc_routers.append(route)
			elif re.search("asab", path):
				L.warning("asab in path: {}".format(path))
				asab_routers.append(route)
			else:
				L.warning("asab NOT in path: {}".format(path))
				service_routers.append(route)



		for route in service_routers:
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			path_object = specs['paths'].get(path)
			if path_object is None:
				specs['paths'][path] = path_object = {}

			if inspect.ismethod(route.handler):
				if route.handler.__name__ == "validator":
					json_schema = route.handler.__getattribute__("json_schema")
					doc_str = route.handler.__getattribute__("func").__doc__

					method_dict["requestBody"] = {
						"content": {
							"application/json": {
								"schema": json_schema
							}
						},
					}
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__getattribute__("func").__name__)

				else:
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
					doc_str = route.handler.__doc__

			else:
				handler_name = str(route.handler)
				doc_str = route.handler.__doc__

			add_dict = None

			if doc_str is not None:
				doc_str = inspect.cleandoc(doc_str)
				i = doc_str.find("\n---\n")
				if i >= 0:
					self.description = doc_str[:i]
					try:
						add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
					except yaml.YAMLError as e:
						L.error("Failed to parse '{}' doc string {}".format(handler_name, e))
				else:
					self.description = doc_str
			else:
				self.description = ""

			self.description += '\n\nHandler: `{}`'.format(handler_name)

			method_dict.update({
				'summary': self.description.split("\n")[0],
				'description': self.description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				},
			})

			if len(parameters) > 0:
				method_dict['parameters'] = parameters

			if add_dict is not None:
				method_dict.update(add_dict)

			path_object[route.method.lower()] = method_dict


		for route in asab_routers:
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			path_object = specs['paths'].get(path)
			if path_object is None:
				specs['paths'][path] = path_object = {}

			if inspect.ismethod(route.handler):
				if route.handler.__name__ == "validator":
					json_schema = route.handler.__getattribute__("json_schema")
					doc_str = route.handler.__getattribute__("func").__doc__

					method_dict["requestBody"] = {
						"content": {
							"application/json": {
								"schema": json_schema
							}
						},
					}
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__getattribute__("func").__name__)

				else:
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
					doc_str = route.handler.__doc__

			else:
				handler_name = str(route.handler)
				doc_str = route.handler.__doc__

			add_dict = None

			if doc_str is not None:
				doc_str = inspect.cleandoc(doc_str)
				i = doc_str.find("\n---\n")
				if i >= 0:
					self.description = doc_str[:i]
					try:
						add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
					except yaml.YAMLError as e:
						L.error("Failed to parse '{}' doc string {}".format(handler_name, e))
				else:
					self.description = doc_str
			else:
				self.description = ""

			self.description += '\n\nHandler: `{}`'.format(handler_name)

			method_dict.update({
				'summary': self.description.split("\n")[0],
				'description': self.description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				},
			})

			if len(parameters) > 0:
				method_dict['parameters'] = parameters

			if add_dict is not None:
				method_dict.update(add_dict)

			path_object[route.method.lower()] = method_dict



	def build_swagger_specs_all(self):
		"""
		Takes a docstring of a class and a docstring of methods and merges them
		into a Swagger specification.
		"""

		doc_str = self.App.__doc__
  
		self.add_dict = None

		if doc_str is not None:
			doc_str = inspect.cleandoc(doc_str)
			i = doc_str.find("\n---\n")
			if i >= 0:
				self.description = doc_str[:i]
				try:
					self.add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
				except yaml.YAMLError as e:
					L.error("Failed to parse '{}' doc string {}".format(self.App.__class__.__name__, e))
			else:
				self.description = doc_str
		else:
			self.description = ""

		self.specs = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(self.App.__class__.__name__),
				"description": self.description,
				"contact": {
					"name": "ASAB microservice",
					"url": "https://www.github.com/teskalabs/asab",
				},
				"version": "1.0.0"
			},
			"servers": [{"url": "../../"}],  # Base path relative to openapi endpoint
			"paths": {},

			# Authorization
			# TODO: Authorization must not be always of OAuth type
			"components": {},
		}
  
		self.build_swagger_header()
		self.build_swagger_routes()
  
		return self.specs

	def build_swagger_header(self):
     # Get rid of securitySchemes if there is no authorizationUrl or tokenUrl
		if self.AuthorizationUrl and self.TokenUrl:
			self.specs["components"].update({
				"securitySchemes": {
					"oAuth": {
						"type": "oauth2",
						"description": "",
						"flows": {
							"authorizationCode": {
								"authorizationUrl": self.AuthorizationUrl,  # "http://localhost/seacat/api/openidconnect/authorize"
								"tokenUrl": self.TokenUrl,  # "http://localhost/seacat/api/openidconnect/token"
								"scopes": {
									"openid": "Required Scope for OpenIDConnect!",
								}
							}
						}
					}
				},
			})

		# Gets all the scopes from config and puts them into scopes
		if self.Scopes and self.AuthorizationUrl and self.TokenUrl:
			for scope in self.Scopes.split(","):
				self.specs["components"]["securitySchemes"]["oAuth"]["flows"]["authorizationCode"]["scopes"].update({scope: "{} scope.".format(scope.strip().capitalize())})

		# Version from MANIFEST.json
		if self.Manifest:
			self.specs["info"]["version"] = self.Manifest["version"]

		# Show what server/docker container you are on, and it's IP
		self.specs["info"]["description"] = ("Running on: <strong>{}</strong> on: <strong>{}</strong>".format(
			self.App.ServerName, self.WebContainer.Addresses) + "<p>{}</p>".format(self.description))
		# specs["servers"].append({"url": "http://{}:{}".format(server[0], server[1])})

		if self.add_dict is not None:
			self.specs.update(self.add_dict)
   


	def build_swagger_routes(self):
		
		asab_routers = []
		service_routers = []
		doc_routers = []

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			if re.search("/doc", path) or re.search("/oauth-redirect.html", path):
				doc_routers.append(route)
			elif re.search("asab", path):
				L.warning("asab in path: {}".format(path))
				asab_routers.append(route)
			else:
				L.warning("asab NOT in path: {}".format(path))
				service_routers.append(route)



		for route in service_routers:
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			path_object = self.specs['paths'].get(path)
			if path_object is None:
				self.specs['paths'][path] = path_object = {}

			if inspect.ismethod(route.handler):
				if route.handler.__name__ == "validator":
					json_schema = route.handler.__getattribute__("json_schema")
					doc_str = route.handler.__getattribute__("func").__doc__

					method_dict["requestBody"] = {
						"content": {
							"application/json": {
								"schema": json_schema
							}
						},
					}
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__getattribute__("func").__name__)

				else:
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
					doc_str = route.handler.__doc__

			else:
				handler_name = str(route.handler)
				doc_str = route.handler.__doc__

			add_dict = None

			if doc_str is not None:
				doc_str = inspect.cleandoc(doc_str)
				i = doc_str.find("\n---\n")
				if i >= 0:
					description = doc_str[:i]
					try:
						add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
					except yaml.YAMLError as e:
						L.error("Failed to parse '{}' doc string {}".format(handler_name, e))
				else:
					description = doc_str
			else:
				description = ""

			description += '\n\nHandler: `{}`'.format(handler_name)

			method_dict.update({
				'summary': description.split("\n")[0],
				'description': description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				},
			})

			if len(parameters) > 0:
				method_dict['parameters'] = parameters

			if add_dict is not None:
				method_dict.update(add_dict)

			path_object[route.method.lower()] = method_dict


		for route in asab_routers:
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			method_dict = {}

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# Extract URL parameters from formatter string
				path = route_info["formatter"]

				for params in re.findall(r'\{.*\}', path):
					if "/" in params:
						for parameter in params.split("/"):
							parameters.append({
								'in': 'path',
								'name': parameter[1:-1],
								'required': True,
							})
					else:
						parameters.append({
							'in': 'path',
							'name': params[1:-1],
							'required': True,
						})

			else:
				L.warning("Cannot obtain path info from route", struct_data=route_info)
				continue

			path_object = self.specs['paths'].get(path)
			if path_object is None:
				self.specs['paths'][path] = path_object = {}

			if inspect.ismethod(route.handler):
				if route.handler.__name__ == "validator":
					json_schema = route.handler.__getattribute__("json_schema")
					doc_str = route.handler.__getattribute__("func").__doc__

					method_dict["requestBody"] = {
						"content": {
							"application/json": {
								"schema": json_schema
							}
						},
					}
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__getattribute__("func").__name__)

				else:
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
					doc_str = route.handler.__doc__

			else:
				handler_name = str(route.handler)
				doc_str = route.handler.__doc__

			add_dict = None

			if doc_str is not None:
				doc_str = inspect.cleandoc(doc_str)
				i = doc_str.find("\n---\n")
				if i >= 0:
					description = doc_str[:i]
					try:
						add_dict = yaml.load(doc_str[i:], Loader=yaml.SafeLoader)
					except yaml.YAMLError as e:
						L.error("Failed to parse '{}' doc string {}".format(handler_name, e))
				else:
					description = doc_str
			else:
				description = ""

			description += '\n\nHandler: `{}`'.format(handler_name)

			method_dict.update({
				'summary': description.split("\n")[0],
				'description': description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				},
			})

			if len(parameters) > 0:
				method_dict['parameters'] = parameters

			if add_dict is not None:
				method_dict.update(add_dict)

			path_object[route.method.lower()] = method_dict

	# This is the web request handler
	async def doc(self, request):
		'''
		Access the API documentation using a browser.
		---
		tags: ['asab.doc']
		'''

		swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"
		swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css"

		page = '''<!DOCTYPE html>
<html>
<head>
	<link type="text/css" rel="stylesheet" href="{swagger_css_url}">
	<title>{title} API Documentation</title>
</head>
<body>
<div id="swagger-ui">
</div>
<script src="{swagger_js_url}"></script>
	<!-- `SwaggerUIBundle` is now available on the page -->
<script>
window.onload = () => {{
	window.ui = SwaggerUIBundle({{
		url: '{openapi_url}',
		dom_id: '#swagger-ui',
		presets: [
			SwaggerUIBundle.presets.apis,
			SwaggerUIBundle.SwaggerUIStandalonePreset
		]
	}})
}}
</script>
</body>
</html>'''.format(
			title=self.App.__class__.__name__,
			swagger_css_url=swagger_css_url,
			swagger_js_url=swagger_js_url,
			openapi_url="./asab/v1/openapi",
		)

		return aiohttp.web.Response(text=page, content_type="text/html")


	def oauth2_redirect(self, request):
		"""
		Required for the authorization to work.
		---
		tags: ['asab.doc']
		"""
		page = """<!doctype html>
<html lang="en-US">
<head>
	<title>Swagger UI: OAuth2 Redirect</title>
</head>
<body>
<script>
	'use strict';
	function run () {
		var oauth2 = window.opener.swaggerUIRedirectOauth2;
		var sentState = oauth2.state;
		var redirectUrl = oauth2.redirectUrl;
		var isValid, qp, arr;

		if (/code|token|error/.test(window.location.hash)) {
			qp = window.location.hash.substring(1);
		} else {
			qp = location.search.substring(1);
		}

		arr = qp.split("&");
		arr.forEach(function (v,i,_arr) { _arr[i] = '"' + v.replace('=', '":"') + '"';});
		qp = qp ? JSON.parse('{' + arr.join() + '}',
				function (key, value) {
					return key === "" ? value : decodeURIComponent(value);
				}
		) : {};

		isValid = qp.state === sentState;

		if ((
			oauth2.auth.schema.get("flow") === "accessCode" ||
			oauth2.auth.schema.get("flow") === "authorizationCode" ||
			oauth2.auth.schema.get("flow") === "authorization_code"
		) && !oauth2.auth.code) {
			if (!isValid) {
				oauth2.errCb({
					authId: oauth2.auth.name,
					source: "auth",
					level: "warning",
					message: "Authorization may be unsafe, passed state was changed in server. The passed state wasn't returned from auth server."
				});
			}

			if (qp.code) {
				delete oauth2.state;
				oauth2.auth.code = qp.code;
				oauth2.callback({auth: oauth2.auth, redirectUrl: redirectUrl});
			} else {
				let oauthErrorMsg;
				if (qp.error) {
					oauthErrorMsg = "["+qp.error+"]: " +
						(qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
						(qp.error_uri ? "More info: "+qp.error_uri : "");
				}

				oauth2.errCb({
					authId: oauth2.auth.name,
					source: "auth",
					level: "error",
					message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server."
				});
			}
		} else {
			oauth2.callback({auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl});
		}
		window.close();
	}

	if (document.readyState !== 'loading') {
		run();
	} else {
		document.addEventListener('DOMContentLoaded', function () {
			run();
		});
	}
</script>
</body>
</html>"""
		return aiohttp.web.Response(text=page, content_type="text/html")


	async def openapi(self, request):
		'''
		Download OpenAPI (version 3) API documentation (aka Swagger) in YAML.
		---
		tags: ['asab.doc']
		externalDocs:
			description: OpenAPI Specification
			url: https://swagger.io/specification/

		'''
		return aiohttp.web.Response(
			text=(yaml.dump(self.build_swagger_specs_all(), sort_keys=False)),
	
			content_type="text/yaml"
		)

 