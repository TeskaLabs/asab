import ssl
from ..config import ConfigObject


class SSLContextBuilder(ConfigObject):

	ConfigDefaults = {
		'cert': '',  # The certfile string must be the path to a PEM file containing the certificate as well as any number of CA certificates needed to establish the certificate’s authenticity.
		'key': '',  # The keyfile string, if present, must point to a file containing the private key in. Otherwise the private key will be taken from certfile as well.
		'password': '',
		'cafile': '',
		'capath': '',
		'ciphers': '',
		'dh_params': '',

		'verify_mode': '',  # empty or one of CERT_NONE, CERT_OPTIONAL or CERT_REQUIRED
		'check_hostname': '',
		'options': '',
	}

	def build(self, protocol=ssl.PROTOCOL_TLS):
		ctx = ssl.SSLContext(protocol=protocol)

		keyfile = self.Config.get("key")
		if len(keyfile) == 0:
			keyfile = None

		password = self.Config.get("password")
		if len(password) == 0:
			password = None

		cert = self.Config.get("cert")
		if len(cert) != 0:
			ctx.load_cert_chain(
				cert,
				keyfile=keyfile,
				password=password,
			)

		cafile = self.Config.get("cafile")
		if len(cafile) == 0:
			cafile = None

		capath = self.Config.get("capath")
		if len(capath) == 0:
			capath = None

		if (cafile is not None) or (capath is not None):
			ctx.load_verify_locations(cafile=cafile, capath=capath)

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
