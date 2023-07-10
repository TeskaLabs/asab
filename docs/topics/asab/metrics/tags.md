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
Specify the expiration period in the configuration, default is 60 s.

!!! example "Configuration example"

	``` {.}
	[asab:metrics]
	expiration=60
	```

See [webrequests metrics](./built-ins.md#web-requests-metrics) as an example of metrics with dynamic tags.