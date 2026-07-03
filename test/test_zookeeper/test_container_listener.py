import unittest
from unittest import mock

import kazoo.protocol.states

from asab.zookeeper.container import ZooKeeperContainer


class _SockPeer:

	def getpeername(self):
		return ("10.17.211.99", 2181)


class _Conn:

	def __init__(self, sock):
		self._socket = sock


class TestZooKeeperContainerListener(unittest.TestCase):

	def _make_container(self, client_id=None, sock=None):
		container = ZooKeeperContainer.__new__(ZooKeeperContainer)
		container._last_session_id = None
		container._last_connected_node = None
		container.ZooKeeper = mock.Mock()
		container.ZooKeeper.Stopped = False
		container.ZooKeeper.Client = mock.Mock()
		container.ZooKeeper.Client.client_id = client_id
		conn = _Conn(sock) if sock is not None else None
		container.ZooKeeper.Client._connection = conn
		container.ProactorService = mock.Mock()
		container.App = mock.Mock()
		return container

	def test_connected_caches_session_and_node(self):
		container = self._make_container(
			client_id=(0x1038DD926CA0153, b""),
			sock=_SockPeer(),
		)
		with mock.patch.object(ZooKeeperContainer, "_on_connected_at_proactor_thread"):
			with mock.patch("asab.zookeeper.container.L") as log_mock:
				container._listener(kazoo.protocol.states.KazooState.CONNECTED)

		self.assertEqual(container._last_session_id, "0x1038dd926ca0153")
		self.assertEqual(container._last_connected_node, "10.17.211.99:2181")
		log_mock.log.assert_called_once()
		struct_data = log_mock.log.call_args.kwargs["struct_data"]
		self.assertEqual(struct_data["session_id"], "0x1038dd926ca0153")
		self.assertEqual(struct_data["node"], "10.17.211.99:2181")

	def test_suspended_reuses_cached_session_and_node(self):
		container = self._make_container()
		container._last_session_id = "0x1038dd926ca0153"
		container._last_connected_node = "10.17.211.99:2181"
		container.ZooKeeper.Client.client_id = None
		container.ZooKeeper.Client._connection = None

		with mock.patch("asab.zookeeper.container.L") as log_mock:
			container._listener(kazoo.protocol.states.KazooState.SUSPENDED)

		log_mock.warning.assert_called_once()
		struct_data = log_mock.warning.call_args.kwargs["struct_data"]
		self.assertEqual(struct_data["session_id"], "0x1038dd926ca0153")
		self.assertEqual(struct_data["node"], "10.17.211.99:2181")
		self.assertEqual(struct_data["state"], str(kazoo.protocol.states.KazooState.SUSPENDED))


if __name__ == "__main__":
	unittest.main()