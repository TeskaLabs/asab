import unittest
import logging

import asab
import asab.abc


L = logging.getLogger("__name__")



class DiscoveryTestCase(unittest.TestCase):

	def setUp(self):
		super().setUp()
		asab.Config.add_defaults({})
		self.App = asab.Application(args=[], modules=[])



	def tearDown(self):
		asab.abc.singleton.Singleton.delete(self.App.__class__)
		self.App = None
		root_logger = logging.getLogger()
		root_logger.handlers = []


class MockZooKeeperContainer():

	def __init__(self, mock_data):
		self.ZooKeeper = MockZooKeeper(mock_data)
		self.Path = "asab"
		self.ProactorService = MockProactorService()


class MockZooKeeper():

	def __init__(self, mock_data):
		self.MockData = mock_data
		self.Client = MockClient(mock_data)

	async def get_children(self, path):
		steps = path.strip("/").split("/")

		children = self.MockData

		for step in steps:
			children = children.get(step, {}).get("children")
			if children is None:
				return

		return children


	async def get_data(self, path):
		steps = path.strip("/").split("/")
		children = await self.get_children("/".join(steps[:-1]))
		return children.get(steps[-1], {}).get("data")


class MockClient():

	def __init__(self, mock_data):
		self.MockData = mock_data

	def get_children(self, path, watch=None):
		steps = path.strip("/").split("/")

		children = self.MockData

		for step in steps:
			children = children.get(step, {}).get("children")
			if children is None:
				return

		return children


	def get(self, path, watch=None):
		steps = path.strip("/").split("/")
		children = self.get_children("/".join(steps[:-1]))
		return (children.get(steps[-1], {}).get("data"), "this_is_mock")
	
	def exists(self, path):
		return True


class MockProactorService():

	def __init__(self):
		pass

	async def execute(self, func, *args):
		return func(*args)
