#!/usr/bin/env python3
import logging

import asab

L = logging.getLogger(__name__)


class MyApplication(asab.Application):
	'''
	Run this with:
	python3 ./zookeeper.py -c ./zookeeper.conf

	It downloads the configuration file from a zookeeper
	'''


	def __init__(self):
		super().__init__()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
