#!/usr/bin/env python3
import asab
import asab.raft


class MyApplication(asab.Application):

	'''
	Run by:
	$ PYTHONPATH=.. ./raft.py
	'''

	async def initialize(self):
		# Loading the web service module
		self.add_module(asab.raft.Module)

		# Locate raft service
		raftsvc = self.get_service("asab.RaftService")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
