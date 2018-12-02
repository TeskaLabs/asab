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

#

L = logging.getLogger(__name__)

#

class PublicKeyAuthorization(ConfigObject):

	'''
	This is an authorization middleware that uses the whitelist of public keys of authorized clients.
	Clients should provide a certificate via TLS handshake (aka mutual TLS authorization).
	The public key from a certificate is then matched with certificates that are stored in the directory cache.
	A client is authorized when the matching certificate is found, otherwise "HTTPUnauthorized" (401) is raised.

	Client certificates are issued by a dedicated Certificate Authority. You can establish your own.
	A public certificate of the client has to be placed into a client certificate directory of the server.

	This authorization is designed from machine-to-machine websocket communication with small amount of requests.
	It validates the certificate/public keys every time the client hits the server.
	That is OK for long-lived WebSockets, but not scalable for a regular HTTP traffic.

	Example of use: 

	pka = asab.web.auth.publickey.PublicKeyAuthorization(app)
	app.WebContainer.WebApp.middlewares.append(pka.middleware)

	'''

	ConfigDefaults = {
		'pubkeyauth:dir': './',
		'pubkeyauth:glob': '*-cert.pem',
		'pubkeyauth:index': '.index.bin',
		'pubkeyauth:mode': 'ssl', # Or Proxy
		'pubkeyauth:proxy-ssl-header': 'X-Forwarded-Client-Cert', # What header is used to transport client cert
	}

	def __init__(self, app, config_section_name='asab:web:auth:publickey', config=None):
		super().__init__(config_section_name, config)

		self.ClientCertDir = self.Config.get('pubkeyauth:dir')
		self.ClientCertGlob = self.Config.get('pubkeyauth:glob')
		self.IndexPDict = PersistentDict(os.path.join(self.ClientCertDir, self.Config.get('pubkeyauth:index')))

		mode = self.Config.get('pubkeyauth:mode').lower()
		if mode == 'ssl':
			self.middleware = self.middleware_ssl
		elif mode == 'proxy':
			self.middleware = self.middleware_proxy
			self.ProxySSLHeader = self.Config.get('pubkeyauth:proxy-ssl-header')
		else:
			raise RuntimeError("Unknown value '{}' for '{}'".format(mode, 'pubkeyauth:mode'))


	def authorize(self, public_key):
		pk_digest = self.get_public_key_digest(public_key)

		entry = self.IndexPDict.get(pk_digest)
		if entry is None:
			# Key not found in the index, let's scan the directory
			self._scan_dir()
			entry = self.IndexPDict.get(pk_digest)
		
		if entry is None:
			print("Authorization failed - public key not found")
			return False

		assert(entry is not None)

		pk_digest1 = self.get_public_key_digest_from_filename(entry)
		if pk_digest1 is None:
			return False

		return pk_digest == pk_digest1


	def _scan_dir(self):
		known_fnames = frozenset(self.IndexPDict.values())
		for fname in glob.glob(os.path.join(self.ClientCertDir, self.ClientCertGlob)):
			if fname in known_fnames: continue
			pk_digest = self.get_public_key_digest_from_filename(fname)
			self.IndexPDict[pk_digest] = fname


	def get_public_key_digest_from_filename(self, fname):
		try:
			with open(fname, 'rb') as f:
				# Load a client certificate in PEM format
				cert = cryptography.x509.load_pem_x509_certificate(
					f.read(),
					cryptography.hazmat.backends.default_backend()
				)
		except:
			return None

		return self.get_public_key_digest(cert.public_key())


	def get_public_key_digest(self, public_key):
		# Hash the public key
		public_key_bytes = public_key.public_bytes(
			cryptography.hazmat.primitives.serialization.Encoding.DER,
			cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo
		)
		h = hashlib.blake2b(public_key_bytes)
		return h.digest()


	@aiohttp.web.middleware
	async def middleware_proxy(self, request, handler):
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

		cert = request.headers.get(self.ProxySSLHeader)
		if cert is None:
			raise aiohttp.web.HTTPUnauthorized()
		cert = urllib.parse.unquote_to_bytes(cert)

		try:
			cert = cryptography.x509.load_pem_x509_certificate(
				cert,
				cryptography.hazmat.backends.default_backend()
			)
		except:
			L.exception("Error when parsing a client certificate")
			raise aiohttp.web.HTTPUnauthorized()
		
		if not self.authorize(cert.public_key()):
			raise aiohttp.web.HTTPUnauthorized()

		return await handler(request)


	@aiohttp.web.middleware
	async def middleware_ssl(self, request, handler):
		'''
		This middleware is used when ASAB is working directly with SSL socket
		'''
		ssl_object = request.transport.get_extra_info('ssl_object')
		if ssl_object is None:
			# The connection is not a SSL
			raise aiohttp.web.HTTPUnauthorized()

		cert = ssl_object.getpeercert(binary_form=True)
		if cert is None:
			# The client doesn't provided a certificate
			raise aiohttp.web.HTTPUnauthorized()

		try:
			cert = cryptography.x509.load_der_x509_certificate(
				cert,
				cryptography.hazmat.backends.default_backend()
			)
		except:
			L.exception("Error when parsing a client certificate")
			raise aiohttp.web.HTTPUnauthorized()
		
		if not self.authorize(cert.public_key()):
			raise aiohttp.web.HTTPUnauthorized()

		return await handler(request)
