import inspect

import aiohttp
import yaml


class DocWebHandler(object):

	def __init__(self, app, web_container):
		self.App = app
		web_container.WebApp.router.add_get('/doc', self.doc)
		web_container.WebApp.router.add_get('/asab/v1/openapi', self.openapi)

		docstr = app.__doc__
		adddict = None

		if docstr is not None:
			docstr = inspect.cleandoc(docstr)
			i = docstr.find("\n---\n")
			if i >= 0:
				description = docstr[:i]
				adddict = yaml.load(docstr[i:])
			else:
				description = docstr
		else:
			description = ""


		self.SwaggerSpecs = {
			"openapi": "3.0.1",
			"info": {
				"title": "{}".format(app.__class__.__name__),
				"description": description,
				"contact": {
					"name": "ASAB microservice",
					"url": "http://www.github.com/teskalabs/asab",
				},
				"version": "1.0.0"
			},
			"paths": {
			}
		}

		if adddict is not None:
			self.SwaggerSpecs.update(adddict)

		for route in web_container.WebApp.router.routes():
			if route.method == 'HEAD':
				# Skip HEAD methods
				continue

			path = route.get_info()['path']
			pathobj = self.SwaggerSpecs['paths'].get(path)
			if pathobj is None:
				self.SwaggerSpecs['paths'][path] = pathobj = {}

			if inspect.ismethod(route.handler):
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
					adddict = yaml.load(docstr[i:])
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
			if adddict is not None:
				methoddict.update(adddict)

			pathobj[route.method.lower()] = methoddict

	# This is the web request handler
	async def doc(self, request):
		'''
		Acces the API documentation using a browser.
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
			openapi_url="/asab/v1/openapi",
		)

		return aiohttp.web.Response(text=page, content_type="text/html")

	async def openapi(self, request):
		'''
		Download OpenAPI (version 3) API documentation in YAML.
		---
		tags: ['asab.doc']
		externalDocs:
			description: OpenAPI Specification
			url: https://swagger.io/specification/

		'''
		return aiohttp.web.Response(text=yaml.dump(self.SwaggerSpecs), content_type="text/yaml")
