import ssl
from .config import Configurable


class SSLContextBuilder(Configurable):
	"""
	Class for creating SSL context from a configuration.

	Examples:

	```python
	ssl_context_builder = asab.tls.SSLContextBuilder(config_section)
	ssl_context = ssl_context_builder.build(protocol=ssl.PROTOCOL_TLS_CLIENT)
	# ssl_context is later used as a parameter when making HTTP requests
	```
	"""

	ConfigDefaults = {
		'cert': '',  # The certfile string must be the path to a PEM file containing the certificate as well as any number of CA certificates needed to establish the certificate’s authenticity.
		'key': '',  # The keyfile string, if present, must point to a file containing the private key in. Otherwise the private key will be taken from certfile as well.
		'key_password': '',

		# Following three options are fed into SSLContext.load_verify_locations(...)
		'cafile': '',
		'capath': '',
		'cadata': '',

		'ciphers': '',
		'dh_params': '',

		'verify_mode': '',  # empty or one of CERT_NONE, CERT_OPTIONAL or CERT_REQUIRED
		'check_hostname': '',
		'options': '',
	}

	def build(self, protocol=ssl.PROTOCOL_TLS) -> ssl.SSLContext:
		"""
		Create SSL Context for the specified protocol.

		Allowed `protocol` values:

		- ssl.PROTOCOL_TLS
		- ssl.PROTOCOL_TLS_CLIENT: used for the client
		- ssl.PROTOCOL_TLS_SERVER: used for the server

		Args:
			protocol: TLS protocol used for the communication.
		"""
		ctx = ssl.SSLContext(protocol=protocol)

		ctx.options |= ssl.OP_NO_SSLv2
		ctx.options |= ssl.OP_NO_SSLv3

		keyfile = self.Config.get("key")
		if len(keyfile) == 0:
			keyfile = None

		key_password = self.Config.get("key_password")
		if len(key_password) == 0:
			key_password = None

		cert = self.Config.get("cert")
		if len(cert) != 0:
			ctx.load_cert_chain(
				cert,
				keyfile=keyfile,
				password=key_password,
			)

		cafile = self.Config.get("cafile")
		if len(cafile) == 0:
			cafile = None

		capath = self.Config.get("capath")
		if len(capath) == 0:
			capath = None

		cadata = self.Config.get("cadata")
		if len(cadata) == 0:
			cadata = None

		if (cafile is not None) or (capath is not None) or (cadata is not None):
			ctx.load_verify_locations(cafile=cafile, capath=capath, cadata=cadata)

		ciphers = self.Config.get("ciphers")
		if len(ciphers) != 0:
			ctx.set_ciphers(ciphers)

		dh_params = self.Config.get("dh_params")
		if len(dh_params) != 0:
			ctx.load_dh_params(dh_params)

		verify_mode = self.Config.get("verify_mode")
		if len(verify_mode) > 0:
			verify_mode_tx = {
				'CERT_NONE': ssl.CERT_NONE,
				'CERT_OPTIONAL': ssl.CERT_OPTIONAL,
				'CERT_REQUIRED': ssl.CERT_REQUIRED,
			}.get(verify_mode.upper())
			if verify_mode_tx is None:
				raise RuntimeError("Unknown value {}".format(verify_mode))
			ctx.verify_mode = verify_mode_tx

		# TODO: check_hostname > ctx.check_hostname
		# TODO: options > ctx.options

		return ctx
