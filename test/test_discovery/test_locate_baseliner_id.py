from .baseclass import DiscoveryTestCase, MockZooKeeperContainer
from asab.api.discovery import DiscoveryService, DiscoveryResolver


class TestLocate(DiscoveryTestCase):

	MOCK_DATA = {
		"asab": {
			"data": None,
			"children": {
				"run": {
					"data": None,
					"children": {
						"LMIOBaselinerApplication.0000010926": {
							"children": None,
							"data": b"""{
								"host": "lmio-box-testing-3",
								"appclass": "LMIOBaselinerApplication",
								"launch_time": "2024-04-02T10:25:05.028026Z",
								"process_id": 1,
								"instance_id": "lmio-baseliner-1",
								"node_id": "lmio-box-testing-3",
								"service_id": "lmio-baseliner",
								"site_id": "lmio-box-testing",
								"containerized": true,
								"created_at": "2024-04-02T10:15:28.036669Z",
								"version": "v24.14-alpha",
								"discovery": {
									"baselines": [
										"Dataset:default",
										"Host:default",
										"User:default"
									],
									"Dataset:default": [
										"Dataset"
									],
									"Host:default": [
										"Host"
									],
									"User:default": [
										"User"
									]
								},
								"web": [
									[
										"0.0.0.0",
										8989
									],
									[
										"0.0.0.0",
										8989
									],
									[
										"::",
										8989,
										0,
										0
									]
								]
							}"""
						},
					}
				}
			}
		}
	}

	def setUp(self):
		super().setUp()
		self.MockedZKC = MockZooKeeperContainer(mock_data=self.MOCK_DATA)
		self.DiscoveryService = DiscoveryService(self.App, zkc=self.MockedZKC)
		self.DiscoveryResolver = DiscoveryResolver(self.DiscoveryService)
		self.App.Loop.run_until_complete(self.DiscoveryService._get_advertised_instances())


	def test_locate_service_id(self):
		"""
		Compares whether the result is a list with all items in it. However, even though it is a list, the order can be different because sets are being used in the code.
		"""
		res = self.App.Loop.run_until_complete(self.DiscoveryService.locate(service_id="lmio-baseliner"))
		required = ["http://lmio-baseliner-1:8989"]

		self.assertEqual(
			set(res),
			set(required)
		)

		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), len(required))

	def test_locate_baseline_id(self):
		"""
		Compares whether the result is a list with all items in it. However, even though it is a list, the order can be different because sets are being used in the code.
		"""
		res = self.App.Loop.run_until_complete(self.DiscoveryService.locate(baselines="Dataset:default"))
		required = ["http://lmio-baseliner-1:8989"]

		self.assertEqual(
			set(res),
			set(required)
		)

		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), len(required))

	def test_locate_dataset(self):
		"""
		Compares whether the result is a list with all items in it. However, even though it is a list, the order can be different because sets are being used in the code.
		"""
		res = self.App.Loop.run_until_complete(self.DiscoveryService.locate(**{"Dataset:default": "Dataset"}))
		required = ["http://lmio-baseliner-1:8989"]

		self.assertEqual(
			set(res),
			set(required)
		)

		self.assertTrue(isinstance(res, list))
		self.assertEqual(len(res), len(required))
