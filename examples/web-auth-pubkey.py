#!/usr/bin/env python3
import aiohttp.web
import asab.web
import asab.web.auth.publickey

class MyApplication(asab.Application):
	'''
	This is a demonstration of the ASAB Web client ssl cert authorization.
	'''

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.web.Module)

		# Locate web service
		websvc = self.get_service("asab.WebService")

		# Create a dedicated web container
		container = asab.web.WebContainer(websvc, 'example:web', config={
			'ssl:cert': './ssl/cert.pem',
			'ssl:key': './ssl/key.pem',
			'ssl:cafile': './ssl/client-ca-cert.pem',
			'ssl:verify_mode': 'CERT_OPTIONAL',
		})

		# Prepare a authorization middleware
		pka = asab.web.auth.publickey.PublicKeyAuthorization(self, config={
			'pubkeyauth:dir': "./ssl/clients/",

		})
		container.WebApp.middlewares.append(pka.middleware)

		container.WebApp.router.add_get('/', self.handler)


	async def handler(self, request):
		return aiohttp.web.Response(text='Hello world!\n')


if __name__ == '__main__':
	app = MyApplication()
	app.run()
