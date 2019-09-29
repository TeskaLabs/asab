#!/usr/bin/env python3
import aiohttp.web
import asab.web
import asab.web.authn.pubkeyauth

asab.Config.add_defaults({
	'example:web' : {
		'listen': '0.0.0.0 8080 ssl:example:web',
	},

	'ssl:example:web': {
		'cert': './ssl/cert.pem',
		'key': './ssl/key.pem',
		'cafile': './ssl/client-ca-cert.pem',
		'verify_mode': 'CERT_OPTIONAL',
	},

	'authn:pubkey:example:web' : {
		'dir': "./ssl/clients/",
	},

})

class MyApplication(asab.Application):
	'''
	This is a demonstration of the ASAB Web client ssl cert authorization.

	$ cd ~/Workspace/asab/examples/
	$ curl --cacert ./ssl/cert.pem --cert ./ssl/clients/client01-cert.pem --key ./ssl/clients/client01-key.pem https://localhost:8080/

	'''

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'example:web')

		container.WebApp.middlewares.append(
			asab.web.authn.authn_middleware_factory(self, "pubkeyauth:direct")
		)

		container.WebApp.router.add_get('/', self.handler)


	@asab.web.authn.authn_required_handler
	async def handler(self, request, *, identity):
		return aiohttp.web.Response(text='Hello, {}!\n'.format(identity))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
