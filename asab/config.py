import os
import sys
import glob
import logging
import configparser

#

L = logging.getLogger(__name__)

#

class ConfigParser(configparser.ConfigParser):

	_default_values = {

		'general': {
			'verbose': os.environ.get('ASAB_VERBOSE', False),
			'config_file': os.environ.get('ASAB_CONFIG', ''),
			'tick_period': 1, # In seconds
		},

		"logging:rfc5424": {
			"sd_id": "sd",
		},

		"logging:console": {
			"format": "%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s: %%(message)s",
			"datefmt": "%%d-%%b-%%Y %%H:%%M:%%S.%%f",
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

				if "$" in value:
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
