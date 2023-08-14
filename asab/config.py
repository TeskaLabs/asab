import os
import sys
import re
import glob
import logging
import inspect
import platform
import configparser
import urllib.parse
import collections.abc
import typing

from . import utils


L = logging.getLogger(__name__)


class ConfigParser(configparser.ConfigParser):
	"""
	ConfigParser enhanced with new features such as adding default configuration, URL validation, automatic reading from Zookeeper etc.
	"""
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
			"web_requests_metrics": False,  # False is a default, web_requests_metrics won't be generated.
			"expiration": 60,
		},

		"asab:doc": {
			"default_route_tag": "module_name"
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
		},

		"housekeeping": {
			"at": "03:00",
			"limit": "05:00",
			"run_at_startup": "no",
		},

		"sentry": {
			"enabled": "false",
			"dsn": "",
			"environment": "develop",
			"traces_sample_rate": 1.0,
		},

		"sentry:logging": {
			"breadcrumbs": "info",
			"events": "warning"
		}

	}

	if 'ASAB_ZOOKEEPER_SERVERS' in os.environ:
		# If `ASAB_ZOOKEEPER_SERVERS` are specified, use that as a default value
		_default_values['zookeeper'] = {'servers': os.environ['ASAB_ZOOKEEPER_SERVERS']}

	def add_defaults(self, dictionary: dict) -> None:
		"""Add defaults to a current configuration.

		Args:
			dictionary: Arguments to be added to the default configuration.
		"""

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


	def _traverse_includes(self, includes: str, this_dir: str) -> None:
		"""
		Read included config files. Nested including is supported.
		"""
		if '\n' in includes:
			sep = '\n'
		else:
			sep = " "

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
		"""
		This method should be called only once, any subsequent call will lead to undefined behaviour.
		"""
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

		self.add_defaults(ConfigParser._default_values)

		includes = self.get('general', 'include', fallback='')

		self._included = set()
		self._traverse_includes(includes, this_dir=os.path.dirname(config_fname))

		del self._load_dir_stack


	def _include_from_zookeeper(self, zkurl):
		"""
		Load the configuration from a ZooKeeper server and append it to the `self.config_contents_list` attribute.

		The method establishes a connection to the ZooKeeper server specified in the configuration file mentioned above.
		It retrieves the configuration by accessing the path specified in the `general` section, using the key `includes`.
		The server URL is provided as a list of server names: server1, server2, server3.
		The path to the configuration file follows this format: 'zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/asab/etc/zk-site.conf.'

		The loaded configuration is then appended to the `self.config_contents_list` attribute, allowing further processing or usage.
		This method supports loading configuration files in various formats, such as .json, .yaml, and .conf.

		Example:

			```ini
			[asab:zookeeper]
			url=server1 server2 server3
			[general]
			include=zookeeper://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/asab/etc/zk-site.conf.
			```
		"""
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
			# Delayed import to minimize a hard dependency footprint
			import kazoo.client
			import json
			import yaml
			zk = kazoo.client.KazooClient(url_netloc)
			zk.start()
			data = zk.get(url_path)[0]
			if url_path.endswith(".json"):
				config = json.loads(data)
				self.read_dict(config)
			elif url_path.endswith(".yaml"):
				config = yaml.safe_load(data)
				self.read_dict(config)
			elif url_path.endswith(".conf"):
				config = data.decode("utf-8")
				self.read_string(config)
			else:
				raise NotImplementedError("Unknown configuration format '{}'".format(url_path))

			zk.stop()
			zk.close()

			# Include in the list of config file contents
			self.config_contents_list.append(config)

		except Exception as e:
			L.error("Failed to obtain configuration from Zookeeper server(s): '{}'.".format(e))
			sys.exit(1)


	def get_config_contents_list(self):
		return self.config_contents_list, self.config_name_list


	def getseconds(self, section, option, *, raw=False, vars=None, fallback=None, **kwargs) -> float:
		"""
		Get time data from config and convert time string into seconds with `convert_to_seconds()` method.

		The available units are:

		- `y` - years
		- `M` - months
		- `w` - weeks
		- `d` - days
		- `h` - hours
		- `m` - minutes
		- `s` - seconds
		- `ms` - milliseconds

		Returns:
			float: Time in seconds.

		Examples:

		```python
		self.SleepTime = asab.Config["sleep"].getseconds("sleep_time")
		self.AnotherSleepTime = asab.Config.getseconds("sleep", "another_sleep_time")
		```
		"""

		if fallback is None:
			fallback = configparser._UNSET

		return self._get_conv(section, option, utils.convert_to_seconds, raw=raw, vars=vars, fallback=fallback, **kwargs)


	def geturl(self, section, option, *, raw=False, vars=None, fallback=None, scheme=None, **kwargs):
		"""
		Get URL from config and remove all leading and trailing whitespaces and trailing slashes.

		Args:
			scheme (str | tuple): URL scheme(s) awaited. If `None`, scheme validation is bypassed.

		Returns:
			Validated URL.

		Raises:
			ValueError: Scheme requirements are not met if set.

		Examples:

		```ini
		[urls]
		teskalabs=https://www.teskalabs.com/
		github=github.com
		```

		``` python
		asab.Config["urls"].geturl("teskalabs", scheme="https")
		asab.Config.geturl("urls", "github", scheme=None)
		```
		"""
		return utils.validate_url(self.get(section, option, raw=raw, vars=vars, fallback=fallback), scheme)


	def getmultiline(self, section, option, *, raw=False, vars=None, fallback=None, **kwargs) -> typing.List[str]:
		"""
		Get multiline data from config.

		Examples:

		```ini
		[places]
		visited:
			Praha
			Brno
			Pardubice Plzeň
		unvisited:
		```

		```python
		>>> asab.Config.getmultiline("places", "visited")
		["Praha", "Brno", "Pardubice", "Plzeň"]
		>>> asab.Config.getmultiline("places", "unvisited")
		[]
		>>> asab.Config.getmultiline("places", "nonexisting", fallback=["Gottwaldov"])
		["Gottwaldov"]
		```
		"""
		values = self.get(section, option, raw=raw, vars=vars, fallback=fallback)
		if isinstance(values, str):
			return [item.strip() for item in re.split(r"\s+", values) if len(item) > 0]
		else:
			# fallback can be anything
			return values


class _Interpolation(configparser.ExtendedInterpolation):
	"""Interpolation which expands environment variables in values."""


	def before_read(self, parser, section, option, value):
		# Expand environment variables
		if '$' in value:
			os.environ['THIS_DIR'] = os.path.abspath(parser._load_dir_stack[-1])

			value = os.path.expandvars(value)

		return super().before_read(parser, section, option, value)


Config = ConfigParser(interpolation=_Interpolation())
"""
Object for accessing the configuration of the ASAB application.

Examples:

```python
my_conf_value = asab.Config['section_name']['key']
```
"""


class Configurable(object):
	"""
	Custom object whose attributes can be loaded from the configuration.

	Example:
		```python
		class ConfigurableObject(asab.Configurable):

			ConfigDefaults = {
				'foo': 'bar',
			}

			def __init__(self, config_section_name, config=None):
				super().__init__(config_section_name=config_section_name, config=config)

				config_foo = self.Config.get('foo')
		```
	"""

	ConfigDefaults: dict = {}


	def __init__(self, config_section_name: str, config: typing.Optional[dict] = None):
		self.Config = ConfigurableDict()

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


class ConfigurableDict(collections.abc.MutableMapping):
	"""
	A dictionary supplemented with custom methods for obtaining bools, seconds, urls etc.
	"""

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


	def getboolean(self, key) -> bool:
		"""
		Obtain the corresponding value of the key and convert it into bool.
		"""
		value = self._data[key]
		return utils.string_to_boolean(value)


	def getseconds(self, key) -> float:
		"""
		Obtain the corresponding value of the key and convert it into seconds via `convert_to_seconds()` method.
		"""
		value = self._data[key]
		return utils.convert_to_seconds(value)


	def getint(self, key) -> int:
		"""
		Obtain the corresponding value of the key and convert it into integer.
		"""
		value = self._data[key]
		return int(value)


	def getfloat(self, key) -> float:
		"""
		Obtain the corresponding value of the key and convert it into float.
		"""
		value = self._data[key]
		return float(value)


	def geturl(self, key, scheme):
		"""
		Obtain the corresponding value of the key and parse it via `validate_url()` method.
		"""
		value = self._data[key]
		return utils.validate_url(value, scheme)


	def __repr__(self):
		return "<%s %r>" % (self.__class__.__name__, self._data)
