#!/usr/bin/env python3
import asab
import asab.raft


class MyApplication(asab.Application):

	'''
	Run by:
	$ PYTHONPATH=.. ./raft.py
	'''

	async def initialize(self):
		if asab.Config["asab:raft"].getboolean("webapi"):
			from asab import web
			self.add_module(web.Module)

		# Loading the raft service module
		self.add_module(asab.raft.Module)

		# Locate raft service
		raftsvc = self.get_service("asab.RaftService")


if __name__ == '__main__':
	app = MyApplication()
	app.run()
