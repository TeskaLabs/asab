import asab
import asab.metrics
import asab.metrics.influxdb

from .baseclass import MetricsTestCase


class TestValidation(MetricsTestCase):
    def test_counter_01(self):
        """
        Tests if the name validation works
        Influx
        """

        self.MetricsService.create_counter(
            "my, count er",
            tags={"foo": "bar"},
            init_values={"value1": 0, "value2": 0},
        )

        influxdb_format = asab.metrics.influxdb.influxdb_format(
            self.MetricsService.Storage.Metrics, 123.45
        )
        self.assertEqual(
            influxdb_format,
            "".join(
                [
                    "my\\,\\ count\\ er,host=mockedhost.com,foo=bar value1=0i,value2=0i 123450000000\n",
                ]
            ),
        )
        self.MetricsService._flush_metrics()

    def test_counter_02(self):
        """
        Tests if the tag validation works
        Influx
        """

        self.MetricsService.create_counter(
            "mycounter",
            tags={"fo, = o": "ba, = r"},
            init_values={"value1": 0, "value2": 0},
        )

        influxdb_format = asab.metrics.influxdb.influxdb_format(
            self.MetricsService.Storage.Metrics, 123.45
        )
        self.assertEqual(
            influxdb_format,
            "".join(
                [
                    "mycounter,host=mockedhost.com,fo\\,\\ \\=\\ o=ba\\,\\ \\=\\ r value1=0i,value2=0i 123450000000\n",
                ]
            ),
        )
        self.MetricsService._flush_metrics()

    def test_counter_03(self):
        """
        Tests if the field/values validation works
        Influx
        """

        self.MetricsService.create_counter(
            "mycounter",
            tags={"foo": "bar"},
            init_values={"val, ue1": 0, "va,lue 2": 0},
        )

        influxdb_format = asab.metrics.influxdb.influxdb_format(
            self.MetricsService.Storage.Metrics, 123.45
        )
        self.assertEqual(
            influxdb_format,
            "".join(
                [
                    "mycounter,host=mockedhost.com,foo=bar val\\,\\ ue1=0i,va\\,lue\\ 2=0i 123450000000\n",
                ]
            ),
        )
        self.MetricsService._flush_metrics()

    def test_counter_04(self):
        """
        Tests if the field/values validation works but with the value being a string
        Influx
        """

        self.MetricsService.create_counter(
            "mycounter",
            tags={"foo": "bar"},
            init_values={"value1": "test1", "value2": "test2"},
        )

        influxdb_format = asab.metrics.influxdb.influxdb_format(
            self.MetricsService.Storage.Metrics, 123.45
        )
        self.assertEqual(
            influxdb_format,
            "".join(
                [
                    'mycounter,host=mockedhost.com,foo=bar value1="test1",value2="test2" 123450000000\n',
                ]
            ),
        )
        self.MetricsService._flush_metrics()
