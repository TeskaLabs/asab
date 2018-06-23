#!/usr/bin/env python3
import logging
import datetime 

import asab
import asab.raft

#

L = logging.getLogger(__name__)

#

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


	async def main(self):
		# Locate raft service
		self.RaftSVC = self.get_service("asab.RaftService")
		
		ok = await self.RaftSVC.Client.connect()
		if ok:
			self.PubSub.subscribe("Application.tick!", self._on_tick)


	async def _on_tick(self, event_name):
		try:
			await self.RaftSVC.Client.issue_command({'testing': datetime.datetime.now().isoformat()})
		except Exception as e:
			L.error("Raft client error: {}".format(e))


if __name__ == '__main__':
	app = MyApplication()
	app.run()
