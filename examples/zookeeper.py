#!/usr/bin/env python3
import sys
import asab.config
from asab.config import Config


L = asab.config.logging.getLogger(__name__)


class MyApplication(asab.Application):
	'''
	Run this with:
	python3 ./zookeeper.py -c ./zookeeper.conf

	It downloads the configuration file from a zookeeper
	'''

	def __init__(self):
		super().__init__()
		# Get the list with contents of the configuration files and its name respectively
		cont_list, cont_name = Config.get_config_contents_list()
		for list, name in zip(cont_list, cont_name):
			print("Printing config file: " + name)
			print()
			print(list)
		sys.exit(1)


if __name__ == "__main__":
	app = MyApplication()
	app.run()
