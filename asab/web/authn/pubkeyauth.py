import urllib.parse
import hashlib
import os.path
import glob
import logging

import aiohttp.web

import cryptography.x509
import cryptography.hazmat.backends
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization

from ...pdict import PersistentDict
from ...config import ConfigObject
from ... import Service

#

L = logging.getLogger(__name__)

#

'''
This is an authentification that uses public keys of authorized clients.
Clients should provide a certificate via TLS handshake (aka mutual TLS authorization).

Client certificates are issued by a dedicated Certificate Authority. You can establish your own.
A public certificate of the client has to be placed into a client certificate directory of the server.

This authentication is designed from machine-to-machine websocket communication with small amount of requests.
It validates the certificate/public keys every time the client hits the server.
That is OK for long-lived WebSockets, but not scalable for a regular HTTP traffic.

'''



def pubkeyauth_direct_middleware_factory(app, *args, **kwargs):

	@aiohttp.web.middleware
	async def pubkeyauth_direct_middleware(request, handler):
		'''
		This middleware is used when ASAB is working directly with SSL socket
		'''
		ssl_object = request.transport.get_extra_info('ssl_object')
		if ssl_object is None: 
			# The connection is not a SSL
			return await handler(request)

		cert = ssl_object.getpeercert(binary_form=True)
		if cert is None:
			# The client doesn't provided a certificate
			return await handler(request)

		try:
			cert = cryptography.x509.load_der_x509_certificate(
				cert,
				cryptography.hazmat.backends.default_backend()
			)
		except:
			L.exception("Error when parsing a client certificate")
			return await handler(request)
		
		request.Identity = cert.subject.rfc4514_string()

		return await handler(request)

	return pubkeyauth_direct_middleware


def pubkeyauth_proxy_middleware_factory(app, *args, **kwargs):

	@aiohttp.web.middleware
	async def pubkeyauth_proxy_middleware(request, handler):
		'''
		This middleware is used when ASAB is working behind a SSL-terminating proxy.
		Client certificate is expected in X-SSL-Client-Cert

		The client certificate is now extracted from `X-SSL-Client-Cert` header, where is it stored by NGinx by:

		proxy_set_header X-SSL-Client-Cert $ssl_client_escaped_cert;

server {
	listen  443 ssl;

	# A server certificate
	ssl_certificate_key letsencrypt/key.pem;
	ssl_certificate	letsencrypt/fullchain.cer;

	# Certificate of your custom CA for clients
	ssl_trusted_certificate custom-ca-cert.pem;

	# make verification optional, so we can display a 403 message to those who fail authentication
	ssl_verify_client optional_no_ca;

	location /websocket {
		if ($ssl_client_verify != SUCCESS) {
			return 403;
		}

		proxy_pass http://localhost:8080/websocket;
		proxy_http_version 1.1;

		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;

		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "Upgrade";

		proxy_set_header X-Forwarded-Client-Cert $ssl_client_escaped_cert;
	}
}

		'''

		cert = request.headers.get('X-Forwarded-Client-Cert')
		if cert is None:
			return await handler(request)
		cert = urllib.parse.unquote_to_bytes(cert)

		try:
			cert = cryptography.x509.load_pem_x509_certificate(
				cert,
				cryptography.hazmat.backends.default_backend()
			)
		except:
			L.exception("Error when parsing a client certificate")
			return await handler(request)
		
		request.Identity = cert.subject.rfc4514_string()

		return await handler(request)


	return pubkeyauth_proxy_middleware


