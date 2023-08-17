# Metrics

Metrics document the state of the application in a timescale manner. 
For further analysis, connect your ASAB application to a time-series
database. [Influx](https://www.influxdata.com/) and
[Prometheus](https://prometheus.io/) are supported.


!!! example

	``` python
	class MyApplication(asab.Application):
		async def initialize(self):
			from asab.metrics import Module # (1)!
			self.add_module(Module)
			self.MetricsService = self.get_service('asab.MetricsService') # (2)!
			self.MyCounter = self.MetricsService.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0}) # (3)!

	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	```

	1. Import the `asab.metrics` module and add it to the application.
	2. Then, you can localize MetricsService.
	3. Use MetricsService to intialize the counter.


See the full example [here](https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py).

See reference [here](./../../../reference/metrics/service.md).

## Types of Metrics

-   `Gauge` stores single numerical values which can go up and down.
    Implements `set` method to set the metric values.
-   `Counter` is a cumulative metric whose values can increase or decrease. 
    Implements `add` and `sub` methods.
-   Event per Second Counter (`EPSCounter`) divides all values by delta time.
-   `DutyCycle` measures the fraction of a period in which a signal/system is active <https://en.wikipedia.org/wiki/Duty_cycle>
-   `AggregationCounter` allows to `set` values based on an aggregation function.
    `max` function is default.
-   `Histogram` represents cumulative histogram with `set` method.

`Counter`, `AggregationCounter`, and `Histogram` come also in variants
respecting dynamic tags. (See section [Dynamic Tags](./tags.md))

All methods that create new metrics objects can be found in the Metrics
Service reference. You should never initiate a new metrics object on its
own, but always through Metrics Service. Metris initialization is meant
to be done in the init time of your application and **should not be done
during runtime**.

## ASAB Metrics Interpretation

Metrics Service not only creates new metrics but also periodically
collects their values and sends them to selected databases. Every 60
seconds in the application lifetime, Metrics Service gathers values of
all ASAB metrics. All Counters (and metric types that inherit from
`Counter`) reset at this event to their
initial values by default. Interpretation of ASAB Counters is affected
by their resetable nature. Even though they monotonously increase,
resetting every minute gives them a different meaning. In a long-term
observation (that's how you most probably monitor the metrics in
time-series databases), these metrics count **events per minute**. Thus,
resettable Counters are presented to the Prometheus database as gauge-type
metrics. Set the `reset` argument to `False`
when creating a new Counter to disable Counter resetting. This periodic
"flush" cycle also causes 60s delay of metric propagation into
supported time-series databases.
See the Timestamp section explaining the origin of a timestamp in each metric record.

## Initial Values

You can initiate your metric instance **with or without initial values**.
Initial values are always present and presented to databases even without a single event changing the metric values.
You will always find a pair of value name and its value in resulting dataset.
Values (name and value pairs) added during runtime last only 60s.
You might spot this feature as missing values in the resulting time-series dataset.


## Timestamp

**Timestamp** contains the record of the precise moment the metric's
value was created or committed to the database. There are two types of
metrics: resettable (`is_reset` = True) and non-resettable
(`is_reset` = False). To reset a metric means to set it
back to its initial value (for example, back to 0). The metric's type
is determined by the `reset: bool = True` parameter of the metric's
constructor at the moment of creation. We measure values of non-resettable
metrics at the time of their creation (there are several possible
methods depending on the metric's general logic), while
the resettable ones are measured when we reset the data
(which is also the moment of them being sent into the database).

| Metric Type                       | Description / Methods                        | Origin of the timestamp        | is_reset  |
| :-------------------------------- | :------------------------------------------- | :---------------------  | :-------- |
| `Gauge`                           | Stores single numerical values which can go up and down. `set()`  | When value is set. `set()` | **False** |
| `Counter` (*Allows dynamic tags*) | A cumulative metric; values can increase or decrease. Never stops. `add()`, `sub()` | When value is set. `add()` or `sub()` | **False** |
| `Counter` (*Allows dynamic tags*) | A cumulative metric; values can increase or decrease. Set to 0 every 60 seconds. | On `flush()`, every 60 seconds   | **True**  |
| `EPSCounter`                      | Divides the count of events by the time of the application run.      | On `flush()`, every 60 seconds | **False** |
| `EPSCounter`                      | Divides the count of events by the time difference between measurements.   | On `flush()`, every 60 seconds  | **True** |
| `DutyCycle`                      | The fraction of one period in which a signal/system is active. A 60% DC means the signal is on 60% and off 40% of the time.   | On `flush()`, every 60 seconds | **True** |
| `Aggregation Counter` (*Allows dynamic tags*) | Keeps track of max or min value of the Counter. Keeps maximum value by default.  | When value is set. `set()` | **False** |
| `Aggregation Counter` (*Allows dynamic tags*)| Keeps track of max or min value of the Counter in each 60s window. Keeps maximum value by default. | On `flush()`, every 60 seconds | **True** |
| `Histogram`  (*Allows dynamic tags*) | Cumulative histogram with a `set()` method.      | When value is set. `set()` | **False** |
| `Histogram`  (*Allows dynamic tags*) | Cumulative histogram with a `set()` method. | On `flush()`, every 60 seconds | **True** |


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


# Tags
Tags allow filtering and aggregating collected metrics.
They provide dimensions for further analysis of the collected data.
There are two means of assigning a tag to a metric. Static tags are given to the metric when it is initialized.
Dynamic tags are assigned whenever a value is set.

## Static Tags
!!! example

	``` python
	MyCounter = MetricsService.create_counter(
		"mycounter",
		tags={'origin': 'MyApplication'},
		init_values={'v1': 0, 'v2': 0}
	)
	```

You can see the new tag `origin` in the initialization of `MyCounter`. You can locate the origin of each record in the time-series database by this tag.
To make tracking of each metric record easier, there are several built-in static tags.

### Built-in Tags

- `host`: 
Hostname of the server or machine where the application is running.

- `appclass`: 
Name of the application. It is the name of the class that inherits from the ASAB Application object.

- `node_id`: 
Present if NODE_ID environmental variable is specified. It names a node in the cluster.

- `service_id`: 
Present if SERVICE_ID environmental variable is specified. It names a service in the cluster.

- `instance_id`: 
Present if INSTANCE_ID environmental variable is specified. It names an instance in the cluster.


## Dynamic Tags
!!! example

	``` python
	MyCounter = MetricsService.create_counter(
		"mycounter",
		tags={'origin': 'MyApplication'},
		init_values={'v1': 0, 'v2': 0},
		dynamic_tags=True
	)

	MyCounter.add("v1", 1, {"method": "GET"}):
	```
Some metric types (Counter, AggregationCounter, Histogram) allow you to
use dynamic tags.
You can create values with a specific tag-set during runtime.
Specific tag-sets expire after a defined period.
This might be spotted in your time-series database like a mysterious disappearance of unused tags.
Specify the expiration period in the configuration, default is 60s.

!!! example "Configuration example"

	``` {.}
	[asab:metrics]
	expiration=60
	```

See [webrequests metrics](./built-ins.md#web-requests-metrics) as an example of metrics with dynamic tags.

# Built-in Metrics

## Web Requests Metrics

ASAB `WebService` class automatically
provides metrics counting web requests. There are 5 metrics quantifying
requests to all ASAB endpoints. They use dynamic tags to provide infromation about method, path and status of the response.

-   `web_requests` - Counts requests to asab endpoints as
    events per minute.
-   `web_requests_duration` - Counts total requests
    duration to asab endpoints per minute.
-   `web_requests_duration_min` - Counts minimal request
    duration to asab endpoints per minute.
-   `web_requests_duration_max` - Counts maximum request
    duration to asab endpoints per minute.
-   `web_requests_duration_hist` - Cumulative histogram
    counting requests in buckets defined by the request duration.

Web Requests Metrics are switched off by default. Use configuration to allow them.
Be aware that both the Web module and Metrics module must be initialized for these metrics.

!!! example "Configuration example"
    ``` {.}
    [asab:metrics]
    web_requests_metrics=true
    ```

## Native Metrics

You can opt out of Native Metrics through configuration by setting
`native_metrics` to `false`. Default is `true`.

!!! example "Configuration example"
    ``` {.}
    [asab:metrics]
    native_metrics=true
    ```

### Memory Metrics

A gauge with the name `os.stat` gathers information about memory usage
by your application.

You can find several metric values there:

-   VmPeak - Peak virtual memory size
-   VmLck - Locked memory size
-   VmPin - Pinned memory size
-   VmHWM - Peak resident set size (\"high water mark\")
-   VmRSS - Resident set size
-   VmData, VmStk, VmExe - Size of data, stack, and text segments
-   VmLib - Shared library code size
-   VmPTE - Page table entries size
-   VmPMD - Size of second-level page tables
-   VmSwap - Swapped-out virtual memory size by anonymous private pages;
    shmem swap usage is not included

### Logs Counter

There is a default Counter named `logs` with values `warnings`,
`errors`, and `critical`, counting logs with respective levels. It is a
humble tool for application health monitoring.