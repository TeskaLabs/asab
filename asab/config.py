import os
import sys
import glob
import logging
import inspect
import platform
import configparser
import urllib.parse
import collections.abc

from . import utils


L = logging.getLogger(__name__)


class ConfigParser(configparser.ConfigParser):
	_syslog_sockets = {
		'Darwin': '/var/run/syslog'
	}

	_syslog_format = {
		'Darwin': 'm'
	}

	_default_values = {

		'general': {
			'config_file': os.environ.get('ASAB_CONFIG', ''),
			'tick_period': 1,  # In seconds
			'var_dir': os.path.expanduser('~/.' + os.path.splitext(os.path.basename(sys.argv[0]))[0]),

			'changelog': '',
			'manifest': '',

			# Daemonization
			'pidfile': '!',  # '!' has a special meaning => it transforms into platform specific location of pid file
			'working_dir': '.',
			'uid': '',
			'gid': '',
		},

		"asab:metrics": {
			"native_metrics": "true",
			"expiration": 60,
		},

		"logging": {
			'verbose': os.environ.get('ASAB_VERBOSE', False),
			"app_name": os.path.basename(sys.argv[0]),
			"sd_id": "sd",  # Structured data id, see RFC5424
			"level": "NOTICE",
			"levels": "",
		},

		"logging:console": {
			"format": "%(asctime)s %(levelname)s %(name)s %(struct_data)s%(message)s",
			"datefmt": "%d-%b-%Y %H:%M:%S.%f",
		},

		"logging:syslog": {
			"enabled": "false",
			# TODO: "facility": 'local1',
			"address": _syslog_sockets.get(platform.system(), "/dev/log"),
			"format": _syslog_format.get(platform.system(), "3"),
		},

		"logging:file": {
			"path": "",
			"format": "%(asctime)s %(levelname)s %(name)s %(struct_data)s%(message)s",
			"datefmt": "%d-%b-%Y %H:%M:%S.%f",
			"backup_count": 3,
			"backup_max_bytes": 0,
			"rotate_every": "",
		},

		"authz": {
			# RBAC URL
			# If !DISABLED! is specified, all authorization checks will be skipped
			"rbac_url": "http://localhost:8081/rbac",
		},

		"library": {
			"azure_cache": "false",  # true or the actual path of where the cache should be located
		},

		# "passwords" section serves to securely store passwords
		# in the configuration file; the passwords are not
		# shown in the default API
		#
		# Usage in the configuration file:
		#
		# [connection:KafkaConnection]
		# password=${passwords:kafka_password}
		#
		# [passwords]
		# kafka_password=<MY_SECRET_PASSWORD>
		"passwords": {
		}
	}


	def add_defaults(self, dictionary):
		""" Add defaults to a current configuration """

		for section, keys in dictionary.items():
			section = str(section)

			if section not in self._sections:
				try:
					self.add_section(section)
				except ValueError:
					if self._strict:
						raise

			for key, value in keys.items():

				key = self.optionxform(str(key))
				if key in self._sections[section]:
					# Value exists, no default needed
					continue

				if value is not None:
					value = str(value)

				if value is not None and "$" in value:
					self.set(section, key, os.path.expandvars(value))
				else:
					self.set(section, key, value)


	def _traverse_includes(self, includes, this_dir):
		""" Reads included config files. Supports nested including. """
		if '\n' in includes:
			sep = '\n'
		else:
			sep = os.pathsep

		for include_glob in includes.split(sep):
			include_glob = include_glob.strip()

			if len(include_glob) == 0:
				continue

			if include_glob.startswith("zookeeper"):
				self._include_from_zookeeper(include_glob)

			include_glob = os.path.expandvars(include_glob.strip())

			for include in glob.glob(include_glob):
				include = os.path.abspath(include)

				if include in self._included:
					# Preventing infinite dependency looping
					L.warn("Config file '{}' can be included only once.".format(include))
					continue

				self._included.add(include)
				self.set('general', 'include', '')

				self._load_dir_stack.append(os.path.dirname(include))
				try:
					self.read(include)
				finally:
					self._load_dir_stack.pop()

				includes = self.get('general', 'include', fallback='')
				self._traverse_includes(includes, os.path.dirname(include_glob))


	def _load(self):
		""" This method should be called only once, any subsequent call will lead to undefined behaviour """
		self._load_dir_stack = []
		self.config_contents_list = []
		self.config_name_list = []

		config_fname = ConfigParser._default_values['general']['config_file']
		if config_fname != '':
			if not os.path.isfile(config_fname):
				print("Config file '{}' not found".format(config_fname), file=sys.stderr)
				sys.exit(1)

			self._load_dir_stack.append(os.path.dirname(config_fname))
			try:
				self.read(config_fname)
			finally:
				self._load_dir_stack.pop()

		includes = self.get('general', 'include', fallback='')

		self._included = set()
		self._traverse_includes(includes, this_dir=os.path.dirname(config_fname))

		self.add_defaults(ConfigParser._default_values)

		del self._load_dir_stack


	def _include_from_zookeeper(self, zkurl):
		# parse include value into hostname and path
		url_pieces = urllib.parse.urlparse(zkurl)
		url_path = url_pieces.path
		url_netloc = url_pieces.netloc

		if not url_netloc:
			if "asab:zookeeper" in self:
				# Backward compatibility
				url_netloc = self["asab:zookeeper"]["servers"]
			else:
				url_netloc = self["zookeeper"]["servers"]

		if url_path.startswith("./"):
			if "asab:zookeeper" in self:
				# Backward compatibility
				url_path = self["asab:zookeeper"]["path"] + url_path[1:]
			else:
				url_path = self["zookeeper"]["path"] + url_path[1:]

		head, tail = os.path.split(url_path)
		self.config_name_list.append(tail)

		try:
			# Delayed import to minimize a hard dependecy footprint
			import kazoo.client
			zk = kazoo.client(url_netloc)
			zk.start()
			data = zk.get(url_path)
			# convert bytes to string
			encode_config = str(data, 'utf-8')
			self.read_string(encode_config)
			# Include in the list of config file contents
			self.config_contents_list.append(encode_config)
			zk.close()
		except Exception as e:
			L.error("Failed to obtain configuration from Zookeeper server(s): '{}'.".format(e))
			sys.exit(1)


	def get_config_contents_list(self):
		return self.config_contents_list, self.config_name_list


	def getseconds(self, section, option, *, raw=False, vars=None, fallback=None, **kwargs):
		if fallback is None:
			fallback = configparser._UNSET

		return self._get_conv(section, option, utils.convert_to_seconds, raw=raw, vars=vars, fallback=fallback, **kwargs)


	def geturl(self, section, option, raw=False, vars=None, fallback=None, scheme=None, **kwargs):
		"""Gets URL from config and removes all leading and trailing
		whitespaces and trailing slashes.

		:param scheme: URL scheme(s) awaited. If None, scheme validation is bypassed.
		:type scheme: str, tuple
		:return: validated URL, raises ValueError when scheme requirements are not met if set.
		"""
		return utils.validate_url(self.get(section, option, raw=False, vars=None, fallback=fallback), scheme)


class _Interpolation(configparser.ExtendedInterpolation):
	"""Interpolation which expands environment variables in values."""


	def before_read(self, parser, section, option, value):
		# Expand environment variables
		if '$' in value:
			os.environ['THIS_DIR'] = os.path.abspath(parser._load_dir_stack[-1])

			value = os.path.expandvars(value)

		return super().before_read(parser, section, option, value)


Config = ConfigParser(interpolation=_Interpolation())


class Configurable(object):
	'''
	Usage:
	class ConfigurableObject(asab.Configurable):

		ConfigDefaults = {
			'foo': 'bar',
		}

		def __init__(self, config_section_name, config=None):
			super().__init__(config_section_name=config_section_name, config=config)

			config_foo = self.Config.get('foo')

	'''

	ConfigDefaults = {}


	def __init__(self, config_section_name, config=None):
		self.Config = ConfigObjectDict()

		for base_class in inspect.getmro(self.__class__):
			if not hasattr(base_class, 'ConfigDefaults'):
				continue
			if len(base_class.ConfigDefaults) == 0:
				continue

			# Merge config defaults of each base class in the 'inheritance' way
			for key, value in base_class.ConfigDefaults.items():

				if value is None:
					raise ValueError("None value not allowed in ConfigDefaults. Found in %s:%s " % (
						config_section_name, key))

				if key not in self.Config:
					self.Config[key] = value

		if Config.has_section(config_section_name):
			for key, value in Config.items(config_section_name):
				self.Config[key] = value

		if config is not None:
			self.Config.update(config)


# This is for backward compatibility
ConfigObject = Configurable


class ConfigObjectDict(collections.abc.MutableMapping):


	def __init__(self):
		self._data = {}


	def __getitem__(self, key):
		return self._data[key]


	def __setitem__(self, key, value):
		self._data[key] = value


	def __delitem__(self, key):
		del self._data[key]


	def __iter__(self):
		return iter(self._data)


	def __len__(self):
		return len(self._data)


	def getboolean(self, key):
		value = self._data[key]
		if isinstance(value, bool):
			return value
		if value.lower() not in configparser.ConfigParser.BOOLEAN_STATES:
			raise ValueError("Not a boolean: {}".format(value))
		return configparser.ConfigParser.BOOLEAN_STATES[value.lower()]


	def getseconds(self, key):
		value = self._data[key]
		return utils.convert_to_seconds(value)


	def getint(self, key):
		value = self._data[key]
		return int(value)


	def getfloat(self, key):
		value = self._data[key]
		return float(value)


	def geturl(self, key, scheme):
		value = self._data[key]
		return utils.validate_url(value, scheme)


	def __repr__(self):
		return "<%s %r>" % (self.__class__.__name__, self._data)
