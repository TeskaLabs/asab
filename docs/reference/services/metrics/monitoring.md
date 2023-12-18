# Monitoring
The Metrics module in ASAB serves to produce data - metrics. It does not store nor analyze the data. To get some overview, you must collect the metrics in a time-series database, or choose some custom way of monitoring.
InfluxDB and Prometheus databases are supported by ASAB, and several endpoints can be used for data monitoring or collecting as well.

## InfluxDB

Metrics can be collected in the Influx time-series database. Metrics are being sent in 60s intervals to configured Influx instance.

!!! example "Configuration example"
	``` {.}
	[asab:metrics]
	target=influxdb

	[asab:metrics:influxdb]
	url=http://localhost:8086/
	bucket=my_bucket
	org=my_org
	token=my_token
	```

**InfluxDB 2.0 API parameters**:

-   **url** - (required) URL string of your InfluxDB.
-   **bucket** - (required) Destination bucket for writing.
-   **org** - (required) Destination organization for writing.
-   **orgid** - (optional) ID of the destination organization for writing.
    :   (NOTE: If both orgID and org are specified, org takes
        precedence)
-   **token** - (required) API token to authenticate to the InfluxDB

**InfluxDB \<1.8 API parameters**:
-   **url** - (required) URL string of your InfluxDB.
-   **username** - (required) name of InfluxDB user.
-   **password** - (required) password of InfluxDB user.

## Prometheus
Prometheus is a "pull model" time-series database.
Prometheus accesses `asab/v1/metrics` endpoint of ASAB ApiService. Thus, connecting ASAB to
Prometheus requires APIService initialization. All other configuration is required on the Prometheus side.
ASAB metrics are presented to Prometheus in [OpenMetrics](https://openmetrics.io/) standard format.

!!! example "ApiService initialization"

	``` python
	class MyApplication(asab.Application):
		async def initialize(self):
			from asab.metrics import Module
			self.add_module(Module)
			self.MetricsService = self.get_service('asab.MetricsService')
			self.MyCounter = self.MetricsService.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})

			# Initialize API service
			self.ApiService = asab.api.ApiService(self)
			self.ApiService.initialize_web()

	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	```

!!! example "prometheus.yaml configuration file example"

	``` {.yaml}
	global:
	scrape_interval: 15s
	scrape_timeout: 10s
	evaluation_interval: 15s

	scrape_configs:
	- job_name: 'metrics_example'
	metrics_path: '/asab/v1/metrics'
	scrape_interval: 10s
	static_configs:
	- targets: ['127.0.0.1:8080']
	```

!!! note

	To satisfy the OpenMetrics format required by Prometheus, you should
	follow the instructions below:

	-   Metrics names must fit regex `[a-zA-Z:][a-zA-Z0-9_:]*`. (Any other
		characters are replaced by an underscore. Leading underscores and
		numbers are stripped. These changes proceed without warning.)
	-   Metrics names MUST NOT end with "total" or "created".
	-   Tags SHOULD contain items "unit" and "help" providing metadata to
		Prometheus.
	-   Values MUST be float or integer.

## Metrics Endpoints

The **API Service** in ASAB offers several endpoints that monitor
internal ASAB functionality. Some of them present the current state of
metrics. Check for Swagger documentation of your ASAB Application REST
API by visiting the `/doc` endpoint.

`/asab/v1/metrics`

-   This endpoint returns metrics in OpenMetrics format and its primary
    purpose is to satisfy Prometheus database needs.

`/asab/v1/metrics.json`

-   This endpoint presents metrics data in JSON format.

`/asab/v1/watch_metrics`

-   Use this endpoint for developing or monitoring your app from the
    terminal. It returns a simple table of ASAB metrics. You can filter
    metrics by name using the `filter` parameter and `tags` parameter to
    show or hide tags.

!!! example

	``` {.}
	watch curl localhost:8080/asab/v1/watch_metrics
	```

	``` {.}
	watch curl localhost:8080/asab/v1/watch_metrics?name=web_requests_duration_max,tags=True
	```

## HTTP Target

For use cases requiring a push model of metrics digestion, there is an
HTTP Target. HTTP Target creates a POST request every 60 seconds to configured URL with
the current metrics state sent as JSON body. Configuration is required.

!!! example "Configuration example"
	``` {.}
	[asab:metrics]
	target=http

	[asab:metrics:http]
	url=http://consumer_example:8080/consume
	```
