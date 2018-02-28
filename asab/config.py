import os
import sys
import configparser
import argparse
import logging

#

L = logging.getLogger(__name__)

#

class ConfigParser(configparser.ConfigParser):

	defaults = {

		'general': {
			'verbose': os.environ.get('ASAB_VERBOSE', False),
			'config_file': os.environ.get('ASAB_CONFIG', './etc/asab.conf'),
		},

	}

	def __init__(self):
		super().__init__()

		parser = argparse.ArgumentParser(
			# TODO: should be configurable
			formatter_class=argparse.RawDescriptionHelpFormatter,
			description="Asynchronous Server Application Boilerplate\n(C) 2018 TeskaLabs Ltd\nhttps://www.teskalabs.com/\n",
		)
		parser.add_argument('-c', '--config', help='Specify file path to configuration file')
		parser.add_argument('-v', '--verbose', action='store_true', help='Print more information (enable debug output)')

		args = parser.parse_args()
		if args.config is not None:
			self.defaults['general']['config_file'] = args.config

		if args.verbose:
			self.defaults['general']['verbose'] = True


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

				self.set(section, key, value)


	def load(self):		
		""" This method should be called only once, any subsequent call will lead to undefined behaviour """

		config_fname = self.defaults['general']['config_file']
		if not os.path.isfile(config_fname):
			print("Config file '{}' not found".format(config_fname), file=sys.stderr)
			sys.exit(1)

		self.read(config_fname)

		includes = self.get('general', 'include', fallback='./etc/site.conf')
		for include in includes.split(os.pathsep):
			self.read(include)

		self.add_defaults(self.defaults)

		# Deals with environment variables
		for each_section in self.sections():
			for (each_key, each_val) in self.items(each_section):
				if "$" in each_val:
					self.set(each_section, each_key, os.path.expandvars(each_val))

###

Config = ConfigParser()
