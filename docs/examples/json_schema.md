---
author: Jakub Boukal
commit: 3244e16952cf9398e3cb02329bebea6f0c88b451
date: 2019-12-10 12:34:35+01:00
title: Json schema

---

!!! example

	```python title=json_schema.py linenums="1"
	import aiohttp
	import aiohttp.web
	
	import asab
	import asab.web
	import asab.web.rest
	import asab.web.session
	
	
	class MyApplication(asab.Application):
	
		async def initialize(self):
			# Loading the web service module
			self.add_module(asab.web.Module)
	
			# Locate web service
			websvc = self.get_service("asab.WebService")
	
			# Create a dedicated web container
			container = asab.web.WebContainer(websvc, 'example:web')
	
			# Enable exception to JSON exception middleware
			container.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
	
			# Add routes
			container.WebApp.router.add_post('/api/jsonfile', self.jsonfile)
			print("""
	Test file schema example with curl:
		$ curl http://localhost:8080/api/jsonfile -X POST -H "Content-Type: application/json" -d '{"key2":666}'
	""")
	
			container.WebApp.router.add_post('/api/jsondict', self.jsondict)
			print("""
	Test dict schema example with curl:
		$ curl http://localhost:8080/api/jsondict -X POST -H "Content-Type: application/json" -d '{"key1":"sample text"}'
	or as form
		$ curl http://localhost:8080/api/jsondict -X POST -d "key1=sample%20text"
	""")
	
		@asab.web.rest.json_schema_handler('./data/sample_json_schema.json')
		async def jsonfile(self, request, *, json_data):
			return aiohttp.web.Response(text='Valid data {}\n'.format(json_data))
	
		@asab.web.rest.json_schema_handler({
			'type': 'object',
			'properties': {
				'key1': {'type': 'string'},
				'key2': {'type': 'number'},
			}})
		async def jsondict(self, request, *, json_data):
			return aiohttp.web.Response(text='Valid data {}\n'.format(json_data))
	
	
	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	
	```
