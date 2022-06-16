from .baseclass import MetricsTestCase
import asab.metrics.openmetric
import asab.metrics.influxdb


class TestDutyCycle(MetricsTestCase):

	def test_dutycycle_00(self):
		"""
		Storage wire-format
		"""
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		expectation = {
			"name": "testdc",
			"type": "DutyCycle",
			"fieldset": [{
				"tags": {
					"host": "mockedhost.com",
				},
				"actuals": {
					"v1": {
						"on_off": True,
						"timestamp": 123.45,
						"off_cycle": 0.0,
						"on_cycle": 0.0,
					}
				},
				"values": {}
			}
			]
		}

		self.assertDictEqual(
			my_dutycycle.Storage,
			expectation,
		)


	def test_dutycycle_01(self):
		"""
		Storage wire-format
		dutycycle True
		"""
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		now = 124.45
		my_dutycycle.flush(now)

		expectation = {
			"name": "testdc",
			"type": "DutyCycle",
			"fieldset": [{
				"tags": {
					"host": "mockedhost.com",
				},
				"actuals": {
					"v1": {
						"on_off": True,
						"timestamp": 124.45,
						"off_cycle": 0.0,
						"on_cycle": 0.0,
					}
				},
				"values": {"v1": 1.0}
			}
			]
		}

		self.assertDictEqual(
			my_dutycycle.Storage,
			expectation,
		)

	def test_dutycycle_02(self):
		"""
		Storage wire-format
		dutycycle False
		"""
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		my_dutycycle.set("v1", False)
		now = 124.45
		my_dutycycle.flush(now)

		expectation = {
			"name": "testdc",
			"type": "DutyCycle",
			"fieldset": [{
				"tags": {
					"host": "mockedhost.com",
				},
				"actuals": {
					"v1": {
						"on_off": False,
						"timestamp": 124.45,
						"off_cycle": 0.0,
						"on_cycle": 0.0,
					}
				},
				"values": {"v1": 0.0}
			}
			]
		}

		self.assertDictEqual(
			my_dutycycle.Storage,
			expectation,
		)
