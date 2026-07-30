import copy
import json
import socket

from .baseclass import DiscoveryTestCase, MockZooKeeperContainer
from asab.api.discovery import DiscoveryService


ADVERTISED_NODE = {
	"host": "asab-config-1",
	"appclass": "ASABConfigApplication",
	"instance_id": "asab-config-1",
	"service_id": "asab-config",
	"discovery": {
		"tenant": ["default"],
	},
	"web": [
		["0.0.0.0", 8894],
	],
}


class TestOnChange(DiscoveryTestCase):

	MOCK_DATA = {
		"asab": {
			"data": None,
			"children": {
				"run": {
					"data": None,
					"children": {},
				}
			}
		}
	}

	def setUp(self):
		super().setUp()
		self.MockedZKC = MockZooKeeperContainer(mock_data=self.MOCK_DATA)
		self.DiscoveryService = DiscoveryService(self.App, zkc=self.MockedZKC)
		self.App.Loop.run_until_complete(self.DiscoveryService._rescan_advertised_instances())

	def _set_zk_node(self, name, payload):
		self.MOCK_DATA["asab"]["children"]["run"]["children"][name] = {
			"children": None,
			"data": json.dumps(payload).encode("utf-8"),
		}

	def _delete_zk_node(self, name):
		self.MOCK_DATA["asab"]["children"]["run"]["children"].pop(name, None)

	def test_on_change_created_and_deleted(self):
		item = "ASABConfigApplication.01"
		self._set_zk_node(item, ADVERTISED_NODE)
		data = json.dumps(ADVERTISED_NODE).encode("utf-8")

		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "CREATED", data))

		located = self.App.Loop.run_until_complete(
			self.DiscoveryService.locate(instance_id="asab-config-1")
		)
		self.assertEqual(located, {"http://asab-config-1:8894"})

		discovered = self.App.Loop.run_until_complete(self.DiscoveryService.discover())
		self.assertIn(
			("asab-config-1", 8894, socket.AF_INET),
			discovered["instance_id"]["asab-config-1"],
		)
		self.assertIn(
			("asab-config-1", 8894, socket.AF_INET),
			discovered["tenant"]["default"],
		)

		self._delete_zk_node(item)
		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "DELETED", None))

		located = self.App.Loop.run_until_complete(
			self.DiscoveryService.locate(instance_id="asab-config-1")
		)
		self.assertEqual(located, set())

	def test_on_change_changed(self):
		item = "ASABConfigApplication.01"
		self._set_zk_node(item, ADVERTISED_NODE)
		data = json.dumps(ADVERTISED_NODE).encode("utf-8")
		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "CREATED", data))

		updated = copy.deepcopy(ADVERTISED_NODE)
		updated["web"] = [["0.0.0.0", 9000]]
		self._set_zk_node(item, updated)
		updated_data = json.dumps(updated).encode("utf-8")
		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "CHANGED", updated_data))

		located = self.App.Loop.run_until_complete(
			self.DiscoveryService.locate(instance_id="asab-config-1")
		)
		self.assertEqual(located, {"http://asab-config-1:9000"})

	def test_apply_does_not_mutate_raw_discovery(self):
		item = "ASABConfigApplication.01"
		self._set_zk_node(item, ADVERTISED_NODE)
		data = json.dumps(ADVERTISED_NODE).encode("utf-8")
		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "CREATED", data))

		raw = self.App.Loop.run_until_complete(self.DiscoveryService.discover_raw())
		self.assertEqual(raw[item]["discovery"], {"tenant": ["default"]})
		self.assertNotIn("instance_id", raw[item]["discovery"])
		self.assertNotIn("service_id", raw[item]["discovery"])

	def test_discover_returns_copy(self):
		item = "ASABConfigApplication.01"
		self._set_zk_node(item, ADVERTISED_NODE)
		data = json.dumps(ADVERTISED_NODE).encode("utf-8")
		self.App.Loop.run_until_complete(self.DiscoveryService._on_change(item, "CREATED", data))

		discovered = self.App.Loop.run_until_complete(self.DiscoveryService.discover())
		discovered["instance_id"].clear()

		located = self.App.Loop.run_until_complete(
			self.DiscoveryService.locate(instance_id="asab-config-1")
		)
		self.assertEqual(located, {"http://asab-config-1:8894"})
