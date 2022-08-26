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

		docstr = self.App.__doc__
		adddict = None

		if docstr is not None:
			docstr = inspect.cleandoc(docstr)
			i = docstr.find("\n---\n")
			if i >= 0:
				description = docstr[:i]
				try:
					adddict = yaml.load(docstr[i:], Loader=yaml.SafeLoader)
				except yaml.YAMLError as e:
					L.error("Failed to parse '{}' doc string {}".format(self.App.__class__.__name__, e))
			else:
				description = docstr
		else:
			description = ""

		specs = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(self.App.__class__.__name__),
				"description": description,
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
			self.App.ServerName, self.WebContainer.Addresses) + "<p>{}</p>".format(description))
		# specs["servers"].append({"url": "http://{}:{}".format(server[0], server[1])})

		if adddict is not None:
			specs.update(adddict)

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []
			methoddict = {}

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

			pathobj = specs['paths'].get(path)
			if pathobj is None:
				specs['paths'][path] = pathobj = {}

			if inspect.ismethod(route.handler):
				if route.handler.__name__ == "validator":
					json_schema = route.handler.__getattribute__("json_schema")
					docstr = route.handler.__getattribute__("func").__doc__

					methoddict["requestBody"] = {
						"content": {
							"application/json": {
								"schema": json_schema
							}
						},
					}
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__getattribute__("func").__name__)

				else:
					handler_name = "{}.{}()".format(route.handler.__self__.__class__.__name__, route.handler.__name__)
					docstr = route.handler.__doc__

			else:
				handler_name = str(route.handler)
				docstr = route.handler.__doc__

			adddict = None

			if docstr is not None:
				docstr = inspect.cleandoc(docstr)
				i = docstr.find("\n---\n")
				if i >= 0:
					description = docstr[:i]
					try:
						adddict = yaml.load(docstr[i:], Loader=yaml.SafeLoader)
					except yaml.YAMLError as e:
						L.error("Failed to parse '{}' doc string {}".format(handler_name, e))
				else:
					description = docstr
			else:
				description = ""

			description += '\n\nHandler: `{}`'.format(handler_name)

			methoddict.update({
				'summary': description.split("\n")[0],
				'description': description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				},
			})

			if len(parameters) > 0:
				methoddict['parameters'] = parameters

			if adddict is not None:
				methoddict.update(adddict)

			pathobj[route.method.lower()] = methoddict

		return specs


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
			text=yaml.dump(self.build_swagger_specs()),
			content_type="text/yaml"
		)
