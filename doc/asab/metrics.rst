.. currentmodule:: asab.metrics

Metrics
=======
Metrics document the state of the application in a timescale manner. 
For further analysis, connect your ASAB application to a time-series database. `Influx <https://www.influxdata.com/>`_ and `Prometheus <https://prometheus.io/>`_ are supported.


Metrics Service
------------------------

Create new metrics using :class:`MetricsService`. 

*example of counter initialization:*

.. code:: python 

    class MyApplication(asab.Application):
        async def initialize(self):
            from asab.metrics import Module
            self.add_module(Module)
            self.MetricsService = self.get_service('asab.MetricsService')
            self.MyCounter = self.MetricsService.create_counter("mycounter", tags={'foo': 'bar'}, init_values={'v1': 0, 'v2': 0})

    if __name__ == '__main__':
        app = MyApplication()
        app.run()

See the full example here: https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py



Types of Metrics
---------------

- :class:`Gauge` stores single numerical values which can go up and down. Implements :func:`set` method to set the metric values.
- :class:`Counter` is a cumulative metric whose values can increase or decrease. Implements :func:`add` and :func:`sub` methods.
- Event per Second Counter (:class:`EPSCounter`) divides all values by delta time. 
- :class:`DutyCycle` https://en.wikipedia.org/wiki/Duty_cycle
- :class:`AggregationCounter` allows to :func:`set` values based on an aggregation function. :func:`max` function is default.
- :class:`Histogram` represents cumulative histogram with :func:`set` method.

:class:`Counter`, :class:`AggregationCounter` and :class:`Histogram` come also in variants respecting dynamic tags. (See section :ref:`Dynamic Tags<dynamic_tags>`.)

All methods that create new metrics objects can be found in the Metrics Service reference. You should never initiate a new metrics object on its own, but always through Metrics Service. Metris initialization is meant to be done in the init time of your application and **should not be done during runtime**.


ASAB Metrics Interpretation
----------------------------

Metrics Service not only creates new metrics but also periodically collects their values and sends them to selected databases. 
Every 60 seconds in the application lifetime, Metrics Service gathers values of all ASAB metrics.
All Counters (and metric types that inherit from :class:`Counter`) reset at this event to their initial values by default.
Interpretation of ASAB Counters is affected by their resetable nature. Even though they monotonously increase, resetting every minute gives them a different meaning.
In a long-term observation (that's how you most probably monitor the metrics in time-series databases), these metrics count **events per minute**. 
Thus, resettable Counters are presented to Prometheus database as gauge-type metrics. Set the `reset` argument to `False` when creating a new Counter to disable Counter resetting.
This periodic "flush" cycle also causes 60s delay of metric propagation into supported time-series databases.


Initial Values
--------------
You can initiate your metric instance with or without initial values. When providing initial values, these values are always present and presented to databases even when these values were untouched during the last 60 seconds. You will always see these values in the data, with initial state or changed by occasion.
However, the lifetime of values (name and value pairs) added during runtime is only 60 s. Thus, if this value is not set during 60s period, you won't see it in your database anymore.


.. _dynamic_tags:

Dynamic Tags
------------
Some metric types (Counter, AggregationCounter, Histogram) allow you to use dynamic tags. All metrics in ASAB carry some tags - Hostname by default and others added by custom. 
Using dynamic tags allows you to create values with a specific tag-set during runtime. Specific tag-sets expire after defined period. This might be spotted in your time-series database like a mysterious disappearance of unused tags.
Specify expiration period in confiuration. Default is 60 s.

*example configuration*

.. code::

    [asab:metrics]
    expiration=60


InfluxDB
--------
Metrics can be collected in the Influx time-series database.

*configuration example:*

.. code::

    [asab:metrics]
    target=influxdb

    [asab:metrics:influxdb]
    url=http://localhost:8086/
    bucket=my_bucket
    org=my_org
    token=my_token

**InfluxDB 2.0 API parameters**:

- **url** - [required] url string of your influxDB
- **bucket** - [required] the destination bucket for writes
- **org** - [required] specifies the destination organization for writes
- **orgid** - [optional] specifies the ID of the destination organization for writes
    (NOTE: If both orgID and org are specified, org takes precedence)
- **token** - [required] API token to authenticate to the InfluxDB

**InfluxDB <1.8 API parameters**:

- **url** - [required] url string of your influxDB
- **username** - [required] name of influxDB user
- **password** - [required] password of influxDB user


Prometheus
----------
Prometheus is a "pull model" time-series database.
Prometheus accesses ``asab/v1/metrics`` endpoint of ASAB ApiService. Thus, connecting ASAB to Prometheus requires APIService initialization. However, no more configuration is needed.
ASAB metrics are presented to Prometheus in `OpenMetrics <https://openmetrics.io/>`_ standard format. 


*prometheus.yaml configuration file example:*

.. code:: yaml

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


.. note::

    To satisfy the OpenMetrics format required by Prometheus, you should follow the instructions below:

    - Metrics names must fit regex ``[a-zA-Z:][a-zA-Z0-9_:]*``. (Any other characters are replaced by an underscore. Leading underscores and numbers are stripped. These changes proceed without warning.)
    - Metrics names MUST NOT end with “total” or “created”.
    - Tags SHOULD contain items “unit” and “help” providing metadata to Prometheus.
    - Values MUST be float or integer.


Metrics Endpoints
-----------------
The **API Service** in ASAB offers several endpoints that monitor internal ASAB functionality. Some of them present the current state of metrics.

``/asab/v1/metrics``

- This endpoint returns metrics in OpenMetrics format and its primary purpose is to satisfy Prometheus database needs.

``/asab/v1/metrics.json``

- This endpoint presents metrics data in JSON format.

``/asab/v1/watch_metrics``

- Use this endpoint for developing or monitoring your app from the terminal. It returns a simple table of ASAB metrics. You can filter metrics by name using the ``filter`` parameter and ``tags`` parameter to show or hide tags.

    *example commands:*

.. code::

    watch curl localhost:8080/asab/v1/metrics_watch

.. code::

    watch curl localhost:8080/asab/v1/metrics_watch?name=web_requests_duration_max,tags=True


HTTP Target
-----------
For use cases requiring a push model of metrics digestion, there is an HTTP Target. HTTP Target creates a POST request to configured URL with current metrics state sent as JSON body.
Configuration is required.

*configuration example:*

.. code::

    [asab:metrics]
    target=http

    [asab:metrics:influxdb]
    url=http://consumer_example:8080/consume



Web Requests Metrics
--------------------

There are default metrics in ASAB framework. :class:`WebService` class automatically provides metrics counting web requests. 
There are 5 metrics quantifying requests to all ASAB endpoints. 

- `web_requests` - Counts requests to asab endpoints as events per minute.
- `web_requests_duration` - Counts total requests duration to asab endpoints per minute.
- `web_requests_duration_min` - Counts minimal request duration to asab endpoints per minute.
- `web_requests_duration_max` - Counts maximum request duration to asab endpoints per minute.
- `web_requests_duration_hist` - Cumulative histogram counting requests in buckets defined by the request duration.


Memory Metrics
--------------
A gauge with the name ``os.stat`` gathers information about memory usage by your application.

You can find several metric values there:

- VmPeak - Peak virtual memory size
- VmLck - Locked memory size
- VmPin - Pinned memory size
- VmHWM - Peak resident set size ("high water mark")
- VmRSS - Resident set size
- VmData, VmStk, VmExe - Size of data, stack, and text segments
- VmLib - Shared library code size
- VmPTE - Page table entries size
- VmPMD - Size of second-level page tables
- VmSwap - Swapped-out virtual memory size by anonymous private pages; shmem swap usage is not included

You can opt out of Memory Metrics through configuration by setting `native_metrics` to `false`. Default is `true`.

*example configuration*

.. code::

    [asab:metrics]
    native_metrics=true


Reference
---------

.. autoclass:: MetricsService
    :show-inheritance:

    .. automethod:: create_gauge

        Creates :class:`Gauge` object.

    .. automethod:: create_counter

        Creates :class:`Counter` or :class:`CounterWithDynamicTags` object.

    .. automethod:: create_eps_counter

        Creates :class:`EPSCounter` object.

    .. automethod:: create_duty_cycle

        Creates :class:`DutyCycle` object.

    .. automethod:: create_aggregation_counter

        Creates :class:`AggregationCounter` or :class:`AggregationCounterWithDynamicTags` object.

    .. automethod:: create_histogram

        Creates :class:`Histogram` or :class:`HistogramWithDynamicTags` object.



.. autoclass:: Gauge
    :show-inheritance:

    Argument `init_values` is a dictionary with initial values and value names as keys.

    .. automethod:: set

    :param name: name of the value
    :param value: value itself



.. autoclass:: Counter
    :show-inheritance:

    Argument `init_values` is a dictionary with initial values and value names as keys.
    If reset is True, Counter resets every 60 seconds. 

    .. automethod:: add

    .. automethod:: sub


.. autoclass:: EPSCounter
    :show-inheritance:


.. autoclass:: DutyCycle
    :show-inheritance:

    To initialize DutyCycle, provide an application loop (asab.Application.Loop) as this object tracks the time of the application.


.. autoclass:: AggregationCounter
    :show-inheritance:

    Values (their names and init_values) can be provided when initializing the metrics or added with :func:`set` method.
    :func:`add` and :func:`sub` methods are not implemented.

    .. automethod:: set

    Applies aggregation function on recent Counter value and value in argument and sets the result as new value of the Counter.



.. autoclass:: Histogram
    :show-inheritance:

    .. automethod:: set



.. autoclass:: CounterWithDynamicTags
    :show-inheritance:

    .. automethod:: add

    .. automethod:: sub



.. autoclass:: AggregationCounterWithDynamicTags
    :show-inheritance:

    .. automethod:: set



.. autoclass:: HistogramWithDynamicTags
    :show-inheritance:

    .. automethod:: set

