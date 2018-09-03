import os
import sys
import glob
import logging
import inspect
import platform
import configparser

#

L = logging.getLogger(__name__)

#

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
			'tick_period': 1, # In seconds
			'var_dir': os.path.expanduser('~/.'+os.path.splitext(os.path.basename(sys.argv[0]))[0]),
		
			# Daemonization
			'pidfile': '!', # '!' has a special meaning => it transforms into platform specific location of pid file
			'working_dir': '.',
			'uid': '',
			'gid': '',
		},

		"logging": {
			'verbose': os.environ.get('ASAB_VERBOSE', False),
			"app_name": os.path.basename(sys.argv[0]),
			"sd_id": "sd", # Structured data id, see RFC5424
		},

		"logging:console": {
			"format": "%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s",
			"datefmt": "%%d-%%b-%%Y %%H:%%M:%%S.%%f",
		},

		"logging:syslog": {
			"enabled": "false",
			#TODO: "facility": 'local1',
			"address": _syslog_sockets.get(platform.system(), "/dev/log"),
			"format": _syslog_format.get(platform.system(), "3"),
		},

		"logging:file": {
			"path": "",
			"format": "%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s",
			"datefmt": "%%d-%%b-%%Y %%H:%%M:%%S.%%f",
			"backup_count": 0,
		},

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


	def _load(self):
		""" This method should be called only once, any subsequent call will lead to undefined behaviour """

		config_fname = ConfigParser._default_values['general']['config_file']
		if config_fname != '':
			if not os.path.isfile(config_fname):
				print("Config file '{}' not found".format(config_fname), file=sys.stderr)
				sys.exit(1)

			self.read(config_fname)

		includes = self.get('general', 'include', fallback='')
		for include_glob in includes.split(os.pathsep):
			for include in glob.glob(include_glob):
				self.read(include)

		self.add_defaults(ConfigParser._default_values)

		# Deals with environment variables
		for each_section in self.sections():
			for (each_key, each_val) in self.items(each_section):
				if "$" in each_val:
					self.set(each_section, each_key, os.path.expandvars(each_val))

###

Config = ConfigParser()

###

class ConfigObject(object):

	'''
	Usage:
	class ConfigurableObject(asab.ConfigObject):

		ConfigDefaults = {
			'foo': 'bar',
		}

		def __init__(self, config_section_name, config=None):
			super().__init__(config_section_name=config_section_name, config=config)

			config_foo = self.Config.get('foo')

	'''

	ConfigDefaults = {}


	def __init__(self, config_section_name, config=None):
		self.Config = {}

		for base_class in inspect.getmro(self.__class__):
			if not hasattr(base_class, 'ConfigDefaults'): continue
			if len(base_class.ConfigDefaults) == 0: continue

			# Merge config defaults of each base class in the 'inheritance' way
			for k, v in base_class.ConfigDefaults.items():
				if k not in self.Config:
					self.Config[k] = v

		if config is not None:
			self.Config.update(config)
		
		if Config.has_section(config_section_name):
			for key, value in Config.items(config_section_name):
				self.Config[key] = value
