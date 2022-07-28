import re
import logging
import inspect

import aiohttp
import yaml

##

L = logging.getLogger(__name__)


##


class DocWebHandler(object):

	def __init__(self, app, web_container):
		self.App = app
		self.WebContainer = web_container
		self.WebContainer.WebApp.router.add_get('/doc', self.doc)
		self.WebContainer.WebApp.router.add_get('/asab/v1/openapi', self.openapi)


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
					"url": "http://www.github.com/teskalabs/asab",
				},
				"version": "1.0.0"
			},
			"servers": [{"url": "../../"}],  # Base path relative to openapi endpoint
			"paths": {
			},
		}

		if adddict is not None:
			specs.update(adddict)

		for route in self.WebContainer.WebApp.router.routes():
			if route.method == 'HEAD':
				# Skip HEAD methods
				# TODO: once/if there is graphql, its method name is probably `*`
				continue

			parameters = []

			route_info = route.get_info()
			if "path" in route_info:
				path = route_info["path"]

			elif "formatter" in route_info:
				# TODO: Extract URL parameters from formatter string
				path = route_info["formatter"]

				for m in re.findall(r'\{.*\}', path):
					parameters.append({
						'in': 'path',
						'name': m[1:-1],
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
					parameters.append({
						'in': 'body',
						'name': 'body',
						'required': True,
						'schema': json_schema
					})
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

			methoddict = {
				'description': description,
				'tags': ['general'],
				'responses': {
					'200': {'description': 'Success'}
				}
			}

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
