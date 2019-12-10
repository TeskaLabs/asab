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


def pubkeyauth_middleware_factory(app, *args, mode='direct', service=None, **kwargs):
	'''
	`service` is the instance of `PublicKeyAuthenticationService`.
	If `service` is not provided, every SSL client with certificate is authenticated.

	`mode` is one of `direct` or `proxy`.

	'''

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
		except Exception:
			L.exception("Error when parsing a client certificate")
			return await handler(request)


		if service is not None:
			if not service.authenticate(cert):
				return await handler(request)

		request.Identity = cert.subject.rfc4514_string()

		return await handler(request)

	return pubkeyauth_direct_middleware


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
		except Exception:
			L.exception("Error when parsing a client certificate")
			return await handler(request)

		if service is not None:
			if not service.authenticate(cert):
				return await handler(request)

		request.Identity = cert.subject.rfc4514_string()

		return await handler(request)

	if mode == 'direct':
		return pubkeyauth_direct_middleware
	elif mode == 'proxy':
		return pubkeyauth_proxy_middleware
	else:
		raise RuntimeError("Unknown mode '{}'".format(mode))



class PublicKeyAuthenticationService(Service, ConfigObject):

	'''
	This is an authentication service that uses the whitelist of public keys of authenticated clients.
	Clients should provide a certificate via TLS handshake (aka mutual TLS authorization).
	The public key from a certificate is then matched with certificates that are stored in the directory cache.
	A client is authenticated when the matching certificate is found, otherwise "HTTPUnauthorized" (401) is raised.

	Client certificates are issued by a dedicated Certificate Authority. You can establish your own.
	A public certificate of the client has to be placed into a client certificate directory of the server.

	This authentication is designed from machine-to-machine websocket communication with small amount of requests.
	It validates the certificate/public keys every time the client hits the server.
	That is OK for long-lived WebSockets, but not scalable for a regular HTTP traffic.

	'''

	ConfigDefaults = {
		'dir': './',
		'glob': '*-cert.pem',
		'index': '.index.bin',
	}

	def __init__(self, app, *, service_name="asab.PublicKeyAuthenticationService", config_section_name='asab:web:authn:pubkey', config=None):
		super().__init__(app, service_name)
		ConfigObject.__init__(self, config_section_name, config)

		self.ClientCertDir = self.Config.get('dir')
		self.ClientCertGlob = self.Config.get('glob')
		self.IndexPDict = PersistentDict(os.path.join(self.ClientCertDir, self.Config.get('index')))


	def authenticate(self, certificate):
		public_key = certificate.public_key()
		pk_digest = self.get_public_key_digest(public_key)

		entry = self.IndexPDict.get(pk_digest)
		if entry is None:
			# Key not found in the index, let's scan the directory
			self._scan_dir()
			entry = self.IndexPDict.get(pk_digest)

		if entry is None:
			L.warning("Authentication failed, public key not found")
			return False

		assert(entry is not None)

		pk_digest1 = self.get_public_key_digest_from_filename(entry)
		if pk_digest1 is None:
			return False

		return pk_digest == pk_digest1


	def _scan_dir(self):
		known_fnames = frozenset(self.IndexPDict.values())
		for fname in glob.glob(os.path.join(self.ClientCertDir, self.ClientCertGlob)):
			if fname in known_fnames:
				continue
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
		except Exception:
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
