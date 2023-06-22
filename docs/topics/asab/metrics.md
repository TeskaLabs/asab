xxx {.currentmodule}
asab.metrics
xxx

Metrics
=======

Metrics document the state of the application in a timescale manner. For
further analysis, connect your ASAB application to a time-series
database. [Influx](https://www.influxdata.com/) and
[Prometheus](https://prometheus.io/) are supported.

Metrics Service
---------------

Create new metrics using `MetricsService`{.interpreted-text
role="class"}.

*example of counter initialization:*

``` {.python}
class MyApplication(asab.Application):
    async def initialize(self):
        from asab.metrics import Module
        self.add_module(Module)
        self.MetricsService = self.get_service('asab.MetricsService')
        self.MyCounter = self.MetricsService.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})

if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

See the full example here:
<https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py>

Types of Metrics
----------------

-   `Gauge`{.interpreted-text role="class"} stores single numerical
    values which can go up and down. Implements `set`{.interpreted-text
    role="func"} method to set the metric values.
-   `Counter`{.interpreted-text role="class"} is a cumulative metric
    whose values can increase or decrease. Implements
    `add`{.interpreted-text role="func"} and `sub`{.interpreted-text
    role="func"} methods.
-   Event per Second Counter (`EPSCounter`{.interpreted-text
    role="class"}) divides all values by delta time.
-   `DutyCycle`{.interpreted-text role="class"}
    <https://en.wikipedia.org/wiki/Duty_cycle>
-   `AggregationCounter`{.interpreted-text role="class"} allows to
    `set`{.interpreted-text role="func"} values based on an aggregation
    function. `max`{.interpreted-text role="func"} function is default.
-   `Histogram`{.interpreted-text role="class"} represents cumulative
    histogram with `set`{.interpreted-text role="func"} method.

`Counter`{.interpreted-text role="class"},
`AggregationCounter`{.interpreted-text role="class"} and
`Histogram`{.interpreted-text role="class"} come also in variants
respecting dynamic tags. (See section
`Dynamic Tags<dynamic_tags>`{.interpreted-text role="ref"}.)

All methods that create new metrics objects can be found in the Metrics
Service reference. You should never initiate a new metrics object on its
own, but always through Metrics Service. Metris initialization is meant
to be done in the init time of your application and **should not be done
during runtime**.

ASAB Metrics Interpretation
---------------------------

Metrics Service not only creates new metrics but also periodically
collects their values and sends them to selected databases. Every 60
seconds in the application lifetime, Metrics Service gathers values of
all ASAB metrics. All Counters (and metric types that inherit from
`Counter`{.interpreted-text role="class"}) reset at this event to their
initial values by default. Interpretation of ASAB Counters is affected
by their resetable nature. Even though they monotonously increase,
resetting every minute gives them a different meaning. In a long-term
observation (that\'s how you most probably monitor the metrics in
time-series databases), these metrics count **events per minute**. Thus,
resettable Counters are presented to Prometheus database as gauge-type
metrics. Set the [reset]{.title-ref} argument to [False]{.title-ref}
when creating a new Counter to disable Counter resetting. This periodic
\"flush\" cycle also causes 60s delay of metric propagation into
supported time-series databases.

Initial Values
--------------

You can initiate your metric instance with or without initial values.
When providing initial values, these values are always present and
presented to databases even when these values were untouched during the
last 60 seconds. You will always see these values in the data, with
initial state or changed by occasion. However, the lifetime of values
(name and value pairs) added during runtime is only 60 s. Thus, if this
value is not set during 60s period, you won\'t see it in your database
anymore.

Built-in Tags {#dynamic_tags}
-------------

Tags help you to sort and group metrics in a selected target database,
and analyze the data easily. Several \"static\" tags are provided
directly by ASAB.

%TODO: option%
host
xxx

This is a hostname of the server or machine where the application is
running

%TODO: option%
appclass
xxx

This is the name of the application. It is literally the name of the
class that inherits from the ASAB Application object.

%TODO: option%
node\_id
xxx

Present if NODE\_ID environmental variable is specified. Meant to
specify a node in the cluster. Automatically set by the Remote Control.

%TODO: option%
service\_id
xxx

Present if SERVICE\_ID environmental variable is specified. Meant to
specify a service in the cluster. Automatically set by the Remote
Control.

%TODO: option%
instance\_id
xxx

Present if INSTANCE\_ID environmental variable is specified. Meant to
specify an instance in the cluster. Automatically set by the Remote
Control.

You can use with convenience the three last tags even without Remote
Control by adding the respective environmental variables to Docker
containers (or any other technology you use to run ASAB microservices).

Dynamic Tags
------------

Some metric types (Counter, AggregationCounter, Histogram) allow you to
use dynamic tags. All metrics in ASAB carry some tags - Hostname by
default and others added by custom. Using dynamic tags allows you to
create values with a specific tag-set during runtime. Specific tag-sets
expire after defined period. This might be spotted in your time-series
database like a mysterious disappearance of unused tags. Specify
expiration period in confiuration. Default is 60 s.

*example configuration*

``` {.}
[asab:metrics]
expiration=60
```

Timestamp
---------

**Timestamp** contains the record of the precise moment the metric\'s
value was created or committed to the database. There are two types of
metrics: resettable ([is\_reset]{.title-ref} = True) and non-resettable
([is\_reset]{.title-ref} = False). To reset a metric means to set it
back to its initial value (for example, back to 0). The metric\'s type
is determined by the `reset: bool = True` parameter of the metric\'s
constructor at the moment it is created. We measure non-resettable
metrics at the time of their creation ([there are several possible
methods depending on the metric\'s general logic]{.title-ref}), while
the resettable ones are measured when we send data to the database
([which is also the moment of them being reset]{.title-ref}).

+---+--------+---------------------+--------------+--------------+-----+
|   | Met    | Description /       | Time is      | Timestamp    | is\ |
|   | ric\'s | Methods             | Measured     | Value        | _re |
|   | Type   |                     |              | Appears      | set |
+===+========+=====================+==============+==============+=====+
| 1 | **G    | Stores single       | when metric  | **set()**    | **F |
| F | auge** | numerical values    | is created   | for actual   | als |
|   |        | which can go up and | [(actual     | time         | e** |
|   |        | down.               | time)]       |              |     |
|   |        |                     | {.title-ref} |              |     |
|   |        | **add\_field() /**  |              |              |     |
|   |        | **set()**           |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 2 | **Cou  | A cumulative        | when metric  | **add()** or | **F |
| F | nter** | metric; values can  | is created   | **sub()**    | als |
|   |        | increase or         | [(actual     | for actual   | e** |
|   | [      | decrease Never      | time)]       | time         |     |
|   | Allows | stops.              | {.title-ref} |              |     |
|   | d      |                     |              |              |     |
|   | ynamic | **add\_field() /**  |              |              |     |
|   | tags]  | **add() / sub() /   |              |              |     |
|   | {.titl | flush()**           |              |              |     |
|   | e-ref} |                     |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 2 | **Cou  | A cumulative        | every 60     | **flush()**  | **  |
| T | nter** | metric; values can  | seconds      | - time of    | Tru |
|   |        | increase or         |              | the test     | e** |
|   | [      | decrease Set to 0   |              | flush        |     |
|   | Allows | every 60 seconds.   |              |              |     |
|   | d      |                     |              |              |     |
|   | ynamic | [AgregationCounter  |              |              |     |
|   | tags]  | behavior is based   |              |              |     |
|   | {.titl | on the resettable   |              |              |     |
|   | e-ref} | Co                  |              |              |     |
|   |        | unter.]{.title-ref} |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 3 | **     | There is an         | [\*\*\*\*\*] | [\*\*\*\*\*] | **F |
| F | EPSCou | adjustable reset    | {.title-ref} | {.title-ref} | als |
|   | nter** | parameter in the    |              |              | e** |
|   |        | metric's            |              |              |     |
|   |        | constructor.        |              |              |     |
|   |        |                     |              |              |     |
|   |        | [reset: bool =      |              |              |     |
|   |        | True]{.title-ref}   |              |              |     |
|   |        | [reset: bool =      |              |              |     |
|   |        | False]{.title-ref}  |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 3 | **     | Divides the count   | every 60     | **flush()**  | **  |
| T | EPSCou | of events by the    | seconds      |              | Tru |
|   | nter** | time difference     |              |              | e** |
|   |        | between             |              |              |     |
|   |        | measurements.       |              |              |     |
|   |        |                     |              |              |     |
|   |        | **flush()**         |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 4 | *      | The fraction of one | every 60     | **flush()**  | **  |
| T | *DutyC | period in which a   | seconds      |              | Tru |
|   | ycle** | signal/system is    |              |              | e** |
|   |        | active. A 60% DC    |              |              |     |
|   |        | means the signal is |              |              |     |
|   |        | on 60% and off 40%  |              |              |     |
|   |        | of the time.        |              |              |     |
|   |        |                     |              |              |     |
|   |        | **add\_field() /**  |              |              |     |
|   |        | **set() / flush()** |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 5 | *      | Keeps track of max  | when metric  | **set()**    | **F |
| F | *Aggre | or min value of the | is created   |              | als |
|   | gation | Counter. Maximum    | [(actual     |              | e** |
|   | Cou    | value is a default. | time)]       |              |     |
|   | nter** |                     | {.title-ref} |              |     |
|   |        | **set() /**         |              |              |     |
|   | [      | [+inherits from the |              |              |     |
|   | Allows | C                   |              |              |     |
|   | d      | ounter]{.title-ref} |              |              |     |
|   | ynamic | **add()/sub()**     |              |              |     |
|   | tags]  | [are                |              |              |     |
|   | {.titl | overw               |              |              |     |
|   | e-ref} | ritten]{.title-ref} |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 5 | *      | [\*\*               | every 60     | **flush()**  | **  |
| T | *Aggre | \*\*\*]{.title-ref} | seconds      |              | Tru |
|   | gation |                     |              |              | e** |
|   | Cou    |                     |              |              |     |
|   | nter** |                     |              |              |     |
|   |        |                     |              |              |     |
|   | [      |                     |              |              |     |
|   | Allows |                     |              |              |     |
|   | d      |                     |              |              |     |
|   | ynamic |                     |              |              |     |
|   | tags]  |                     |              |              |     |
|   | {.titl |                     |              |              |     |
|   | e-ref} |                     |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 6 | *      | Represents          | when metric  | **set()**    | **F |
| F | *Histo | cumulative          | is created   |              | als |
|   | gram** | histogram with a    | [(actual     |              | e** |
|   |        | set() method.       | time)]       |              |     |
|   | [      |                     | {.title-ref} |              |     |
|   | Allows | **add\_field() /**  |              |              |     |
|   | d      | **set() / flush()** |              |              |     |
|   | ynamic |                     |              |              |     |
|   | tags]  |                     |              |              |     |
|   | {.titl |                     |              |              |     |
|   | e-ref} |                     |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+
| 6 | *      | [\*\*               | every 60     | **flush()**  | **  |
| T | *Histo | \*\*\*]{.title-ref} | seconds      |              | Tru |
|   | gram** |                     |              |              | e** |
|   |        |                     |              |              |     |
|   | [      |                     |              |              |     |
|   | Allows |                     |              |              |     |
|   | d      |                     |              |              |     |
|   | ynamic |                     |              |              |     |
|   | tags]  |                     |              |              |     |
|   | {.titl |                     |              |              |     |
|   | e-ref} |                     |              |              |     |
+---+--------+---------------------+--------------+--------------+-----+

InfluxDB
--------

Metrics can be collected in the Influx time-series database.

*configuration example:*

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

-   **url** - \[required\] url string of your influxDB

-   **bucket** - \[required\] the destination bucket for writes

-   **org** - \[required\] specifies the destination organization for
    writes

-   

    **orgid** - \[optional\] specifies the ID of the destination organization for writes

    :   (NOTE: If both orgID and org are specified, org takes
        precedence)

-   **token** - \[required\] API token to authenticate to the InfluxDB

**InfluxDB \<1.8 API parameters**:

-   **url** - \[required\] url string of your influxDB
-   **username** - \[required\] name of influxDB user
-   **password** - \[required\] password of influxDB user

Prometheus
----------

Prometheus is a \"pull model\" time-series database. Prometheus accesses
`asab/v1/metrics` endpoint of ASAB ApiService. Thus, connecting ASAB to
Prometheus requires APIService initialization. However, no more
configuration is needed. ASAB metrics are presented to Prometheus in
[OpenMetrics](https://openmetrics.io/) standard format.

*prometheus.yaml configuration file example:*

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

xxx {.note}
xxx {.title}
Note
xxx

To satisfy the OpenMetrics format required by Prometheus, you should
follow the instructions below:

-   Metrics names must fit regex `[a-zA-Z:][a-zA-Z0-9_:]*`. (Any other
    characters are replaced by an underscore. Leading underscores and
    numbers are stripped. These changes proceed without warning.)
-   Metrics names MUST NOT end with "total" or "created".
-   Tags SHOULD contain items "unit" and "help" providing metadata to
    Prometheus.
-   Values MUST be float or integer.
xxx

Metrics Endpoints
-----------------

The **API Service** in ASAB offers several endpoints that monitor
internal ASAB functionality. Some of them present the current state of
metrics. Check for Swagger documentation of your ASAB Application REST
API by visiting the [/doc]{.title-ref} endpoint.

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

*example commands:*

``` {.}
watch curl localhost:8080/asab/v1/watch_metrics
```

``` {.}
watch curl localhost:8080/asab/v1/watch_metrics?name=web_requests_duration_max,tags=True
```

HTTP Target
-----------

For use cases requiring a push model of metrics digestion, there is an
HTTP Target. HTTP Target creates a POST request to configured URL with
current metrics state sent as JSON body. Configuration is required.

*configuration example:*

``` {.}
[asab:metrics]
target=http

[asab:metrics:http]
url=http://consumer_example:8080/consume
```

Web Requests Metrics
--------------------

ASAB `WebService`{.interpreted-text role="class"} class automatically
provides metrics counting web requests. There are 5 metrics quantifying
requests to all ASAB endpoints.

-   [web\_requests]{.title-ref} - Counts requests to asab endpoints as
    events per minute.
-   [web\_requests\_duration]{.title-ref} - Counts total requests
    duration to asab endpoints per minute.
-   [web\_requests\_duration\_min]{.title-ref} - Counts minimal request
    duration to asab endpoints per minute.
-   [web\_requests\_duration\_max]{.title-ref} - Counts maximum request
    duration to asab endpoints per minute.
-   [web\_requests\_duration\_hist]{.title-ref} - Cumulative histogram
    counting requests in buckets defined by the request duration.

Native Metrics
--------------

You can opt out of Native Metrics through configuration by setting
[native\_metrics]{.title-ref} to [false]{.title-ref}. Default is
[true]{.title-ref}.

*example configuration*

``` {.}
[asab:metrics]
native_metrics=true
```

**Memory Metrics**

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

**Logs Counter**

There is a default Counter named `logs` with values `warnings`,
`errors`, and `critical`, counting logs with respective levels. It is a
humble tool for application health monitoring.

Reference
---------

# TODO: autoclass show-inheritance=""}
MetricsService

{.automethod}
create\_gauge

Creates `Gauge`{.interpreted-text role="class"} object.
xxx

{.automethod}
create\_counter

Creates `Counter`{.interpreted-text role="class"} or
`CounterWithDynamicTags`{.interpreted-text role="class"} object.
xxx

{.automethod}
create\_eps\_counter

Creates `EPSCounter`{.interpreted-text role="class"} object.
xxx

{.automethod}
create\_duty\_cycle

Creates `DutyCycle`{.interpreted-text role="class"} object.
xxx

{.automethod}
create\_aggregation\_counter

Creates `AggregationCounter`{.interpreted-text role="class"} or
`AggregationCounterWithDynamicTags`{.interpreted-text role="class"}
object.
xxx

{.automethod}
create\_histogram

Creates `Histogram`{.interpreted-text role="class"} or
`HistogramWithDynamicTags`{.interpreted-text role="class"} object.
xxx
xxx

# TODO: autoclass show-inheritance=""}
Gauge

Argument [init\_values]{.title-ref} is a dictionary with initial values
and value names as keys.

{.automethod}
set
xxx

param name

:   name of the value

param value

:   value itself
xxx

# TODO: autoclass show-inheritance=""}
Counter

Argument [init\_values]{.title-ref} is a dictionary with initial values
and value names as keys. If reset is True, Counter resets every 60
seconds.

{.automethod}
add
xxx

{.automethod}
sub
xxx
xxx

# TODO: autoclass show-inheritance=""}
EPSCounter
xxx

# TODO: autoclass show-inheritance=""}
DutyCycle
xxx

# TODO: autoclass show-inheritance=""}
AggregationCounter

Values (their names and init\_values) can be provided when initializing
the metrics or added with `set`{.interpreted-text role="func"} method.
`add`{.interpreted-text role="func"} and `sub`{.interpreted-text
role="func"} methods are not implemented.

{.automethod}
set
xxx

Applies aggregation function on recent Counter value and value in
argument and sets the result as new value of the Counter.
xxx

# TODO: autoclass show-inheritance=""}
Histogram

{.automethod}
set
xxx
xxx

# TODO: autoclass show-inheritance=""}
CounterWithDynamicTags

{.automethod}
add
xxx

{.automethod}
sub
xxx
xxx

# TODO: autoclass show-inheritance=""}
AggregationCounterWithDynamicTags

{.automethod}
set
xxx
xxx

# TODO: autoclass show-inheritance=""}
HistogramWithDynamicTags

{.automethod}
set
xxx
xxx

# Reference

::: asab.metrics
