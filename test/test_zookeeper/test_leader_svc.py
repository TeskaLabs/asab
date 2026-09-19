import types
import unittest
import unittest.mock

import asab.zookeeper.leader_svc


class LeaderServiceWatchTest(unittest.TestCase):

	def setUp(self):
		service = asab.zookeeper.leader_svc.LeaderService.__new__(
			asab.zookeeper.leader_svc.LeaderService
		)
		service._participating = True
		service._leader_zxid = None
		service._election_thread = unittest.mock.Mock()
		self.proactor_service = unittest.mock.Mock()
		service.ZkContainer = types.SimpleNamespace(ProactorService=self.proactor_service)
		self.service = service

	def test_watch_schedules_election_on_proactor(self):
		self.service._on_change_zookeeper_thread(unittest.mock.sentinel.event)

		self.service._election_thread.assert_not_called()
		self.proactor_service.schedule_threadsafe.assert_called_once_with(
			self.service._election_thread
		)

	def test_watch_does_not_schedule_when_not_participating(self):
		self.service._participating = False

		self.service._on_change_zookeeper_thread(unittest.mock.sentinel.event)

		self.proactor_service.schedule_threadsafe.assert_not_called()

	def test_watch_does_not_schedule_when_already_leader(self):
		self.service._leader_zxid = unittest.mock.sentinel.zxid

		self.service._on_change_zookeeper_thread(unittest.mock.sentinel.event)

		self.proactor_service.schedule_threadsafe.assert_not_called()
