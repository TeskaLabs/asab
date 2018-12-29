import ssl
from ..config import ConfigObject

class SSLContextBuilder(ConfigObject):

	ConfigDefaults = {
		'ssl:cert': '', # The certfile string must be the path to a PEM file containing the certificate as well as any number of CA certificates needed to establish the certificate’s authenticity.
		'ssl:key': '', #The keyfile string, if present, must point to a file containing the private key in. Otherwise the private key will be taken from certfile as well.
		'ssl:password': '',
		'ssl:cafile': '',
		'ssl:capath': '',
		'ssl:ciphers': '',
		'ssl:dh_params': '',

		'ssl:verify_mode': '', # empty or one of CERT_NONE, CERT_OPTIONAL or CERT_REQUIRED
		'ssl:check_hostname': '',
		'ssl:options': '',
	}

	def build(self, protocol=ssl.PROTOCOL_TLS):
		ctx = ssl.SSLContext(protocol=protocol)

		keyfile = self.Config.get("ssl:key")
		if len(keyfile) == 0: keyfile = None
		
		password = self.Config.get("ssl:password")
		if len(password) == 0: password = None

		ctx.load_cert_chain(
			self.Config.get("ssl:cert"),
			keyfile = keyfile,
			password = password,
		)

		cafile = self.Config.get("ssl:cafile")
		if len(cafile) == 0: cafile = None

		capath = self.Config.get("ssl:capath")
		if len(capath) == 0: capath = None

		if (cafile is not None) or (capath is not None):
			ctx.load_verify_locations(cafile=cafile, capath=capath)

		ciphers = self.Config.get("ssl:ciphers")
		if len(ciphers) != 0:
			ctx.set_ciphers(ciphers)

		dh_params = self.Config.get("ssl:dh_params")
		if len(dh_params) != 0:
			ctx.load_dh_params(dh_params)

		verify_mode = self.Config.get("ssl:verify_mode")
		if len(verify_mode) > 0:
			verify_mode_tx = {
				'CERT_NONE': ssl.CERT_NONE,
				'CERT_OPTIONAL': ssl.CERT_OPTIONAL,
				'CERT_REQUIRED': ssl.CERT_REQUIRED,
			}.get(verify_mode.upper())
			if verify_mode_tx is None:
				raise RuntimeError("Unknown value {}".format(verify_mode))
			ctx.verify_mode = verify_mode_tx

		#TODO: ssl:check_hostname > ctx.check_hostname
		#TODO: ssl:options > ctx.options

		return ctx
