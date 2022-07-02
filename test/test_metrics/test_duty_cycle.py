from .baseclass import MetricsTestCase
import asab.metrics.openmetric
import asab.metrics.influxdb


class TestDutyCycle(MetricsTestCase):

	def test_dutycycle_00(self):
		"""
		Storage wire-format
		"""
		self.MetricsService.App = self.MockedLoop
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		expectation = {
			"type": "DutyCycle",
			"name": "testdc",
			'static_tags': {'host': 'mockedhost.com'},
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
				"values": {},
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
		self.MetricsService.App = self.MockedLoop
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
			'static_tags': {'host': 'mockedhost.com'},
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
				"values": {"v1": 1.0},
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
		self.MetricsService.App = self.MockedLoop
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
			'static_tags': {'host': 'mockedhost.com'},
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
				"values": {"v1": 0.0},
			}
			]
		}

		self.assertDictEqual(
			my_dutycycle.Storage,
			expectation,
		)

	def test_dutycycle_03(self):
		"""
		InfluxDB
		"""
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		now = 124.45
		my_dutycycle.flush(now)

		# Test Influx format with init values
		influx_format = asab.metrics.influxdb.influxdb_format(self.MetricsService.Storage.Metrics, 123.45)
		self.assertEqual(
			influx_format,
			''.join([
				'testdc,host=mockedhost.com v1=1.0 123450000000\n',
			])
		)


	def test_dutycycle_04(self):
		"""
		OpenMetric
		"""
		my_dutycycle = self.MetricsService.create_duty_cycle(
			self.MockedLoop,
			"testdc",
			init_values={"v1": True}
		)

		now = 124.45
		my_dutycycle.flush(now)

		# Test OpenMetric output with init values
		om_format = asab.metrics.openmetric.metric_to_openmetric(my_dutycycle.Storage)
		self.assertEqual(
			om_format,
			''.join([
				'# TYPE testdc gauge\n',
				'testdc{host="mockedhost.com",name="v1"} 1.0',
			])
		)
