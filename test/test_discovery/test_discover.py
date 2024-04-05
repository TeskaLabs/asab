from .baseclass import DiscoveryTestCase, MockZooKeeperContainer
from asab.api.discovery import DiscoveryService


class TestDiscover(DiscoveryTestCase):

	MOCK_DATA = {
		"asab": {
			"data": None,
			"children": {
				"run": {
					"data": None,
					"children": {
						"ASABConfigApplication.01": {
							"children": None,
							"data": b"""{
								"host": "asab-config-1",
								"appclass": "ASABConfigApplication",
								"launch_time": "2024-04-03T13:13:39.359729Z",
								"process_id": 1,
								"instance_id": "asab-config-1",
								"node_id": "lmio-eliska-1",
								"service_id": "asab-config",
								"containerized": true,
								"created_at": "2024-02-23T13:06:54.262317Z",
								"version": "v24.08-beta",
								"CI_COMMIT_TAG": "v24.08-beta",
								"CI_COMMIT_REF_NAME": "v24.08-beta",
								"CI_COMMIT_SHA": "014e5a4c23aa034dc5906694f4b14019fc0d581a",
								"CI_COMMIT_TIMESTAMP": "2024-02-20T14:37:58+00:00",
								"CI_JOB_ID": "94807",
								"CI_PIPELINE_CREATED_AT": "2024-02-23T13:05:40Z",
								"CI_RUNNER_ID": "74",
								"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64",
								"web": [
									[
										"0.0.0.0",
										8894
									]
								]
							}"""
						},
						"ASABConfigApplication.02": {
							"children": None,
							"data": b"""{
								"host": "asab-config-2",
								"appclass": "ASABConfigApplication",
								"launch_time": "2024-04-03T13:13:39.359729Z",
								"process_id": 1,
								"instance_id": "asab-config-2",
								"node_id": "lmio-eliska-2",
								"service_id": "asab-config",
								"containerized": true,
								"created_at": "2024-02-23T13:06:54.262317Z",
								"version": "v24.08-beta",
								"CI_COMMIT_TAG": "v24.08-beta",
								"CI_COMMIT_REF_NAME": "v24.08-beta",
								"CI_COMMIT_SHA": "014e5a4c23aa034dc5906694f4b14019fc0d581a",
								"CI_COMMIT_TIMESTAMP": "2024-02-20T14:37:58+00:00",
								"CI_JOB_ID": "94807",
								"CI_PIPELINE_CREATED_AT": "2024-02-23T13:05:40Z",
								"CI_RUNNER_ID": "74",
								"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64",
								"web": [
									[
										"0.0.0.0",
										8894
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
		self.App.Loop.run_until_complete(self.DiscoveryService._get_advertised_instances())


	def test_get_advertised_instances(self):
		res = self.App.Loop.run_until_complete(self.DiscoveryService.get_advertised_instances())
		self.assertEqual(
			res,
			[
				{
					"zookeeper_id": "ASABConfigApplication.01",
					"host": "asab-config-1",
					"appclass": "ASABConfigApplication",
					"launch_time": "2024-04-03T13:13:39.359729Z",
					"process_id": 1,
					"instance_id": "asab-config-1",
					"node_id": "lmio-eliska-1",
					"service_id": "asab-config",
					"containerized": True,
					"created_at": "2024-02-23T13:06:54.262317Z",
					"version": "v24.08-beta",
					"CI_COMMIT_TAG": "v24.08-beta",
					"CI_COMMIT_REF_NAME": "v24.08-beta",
					"CI_COMMIT_SHA": "014e5a4c23aa034dc5906694f4b14019fc0d581a",
					"CI_COMMIT_TIMESTAMP": "2024-02-20T14:37:58+00:00",
					"CI_JOB_ID": "94807",
					"CI_PIPELINE_CREATED_AT": "2024-02-23T13:05:40Z",
					"CI_RUNNER_ID": "74",
					"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64",
					"web": [
						[
							"0.0.0.0",
							8894
						]
					]
				},
				{
					"zookeeper_id": "ASABConfigApplication.02",
					"host": "asab-config-2",
					"appclass": "ASABConfigApplication",
					"launch_time": "2024-04-03T13:13:39.359729Z",
					"process_id": 1,
					"instance_id": "asab-config-2",
					"node_id": "lmio-eliska-2",
					"service_id": "asab-config",
					"containerized": True,
					"created_at": "2024-02-23T13:06:54.262317Z",
					"version": "v24.08-beta",
					"CI_COMMIT_TAG": "v24.08-beta",
					"CI_COMMIT_REF_NAME": "v24.08-beta",
					"CI_COMMIT_SHA": "014e5a4c23aa034dc5906694f4b14019fc0d581a",
					"CI_COMMIT_TIMESTAMP": "2024-02-20T14:37:58+00:00",
					"CI_JOB_ID": "94807",
					"CI_PIPELINE_CREATED_AT": "2024-02-23T13:05:40Z",
					"CI_RUNNER_ID": "74",
					"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64",
					"web": [
						[
							"0.0.0.0",
							8894
						]
					]
				}
			]
		)

	def test_discover(self):
		res = self.DiscoveryService.discover()
		self.assertEqual(
			res,
			{
				"instance_id": {
					"asab-config-1": {("lmio-eliska-1", 8894)},
					"asab-config-2": {("lmio-eliska-2", 8894)}
				},
				"service_id": {
					"asab-config": {("lmio-eliska-1", 8894), ("lmio-eliska-2", 8894)},
				},
			}
		)
