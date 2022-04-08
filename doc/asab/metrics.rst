.. currentmodule:: asab.metrics

Metrics service
===============
Metrics document state of the application in a timescale manner. 
For further analysis, connect your ASAB application to a time-series database. ASAB supports Influx and Prometheus databases.
Default ASAB metrics counting web requests are provided together with :class:`WebService`.


MetricsService
--------------
Create new metrics using :class:`MetricsService`. 

Example of counter initialization:

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

See full example here: https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py



Metrics
-------------

- :class:`Gauge` stores single numerical values which can go up and down. Implements :func:`set` method to set the metric values.
- :class:`Counter` is a cumulative metric whose values can increase or decrease. Implements :func:`add` and :func:`sub` methods.
- Event per Second Counter (:class:`EPSCounter`) divides all values by delta time. 
- :class:`DutyCycle` https://en.wikipedia.org/wiki/Duty_cycle
- :class:`AggregationCounter` allows to :func:`set` values based on an aggregation function. :func:`max` function is default.

All metrics types inherit from :class:`Metric` class.


Enable logging of metrics
-------------------------

Metrics can be displayed in the log of the ASAB application.
In order to enable this, enter following lines in the configuration:

.. code:: ini

    [logging]
    levels=
       asab.metrics INFO

Influx
------
Metrics can be collected in Influx time-series database.

Example of your ASAB application configuration enabeling Influx connection.

.. code:: ini

    [asab:metrics]
    target=influxdb

    [asab:metrics:influxdb]
    url=http://localhost:8086/
    db=mydb

**InfluxDB 2.0 API parameters**:

- url - [required] url string of your influxDB
- bucket - [required] the destination bucket for writes
- org - [required] the parameter value specifies the destination organization for writes
- orgid - [optional] the parameter value specifies the ID of the destination organization for writes
    (NOTE: If both orgID and org are specified, org takes precedence)
- token - [required] API token to authenticate to the InfluxDB

**InfluxDB <1.8 API parameters**:

- url - [required] url string of your influxDB
- username - [required] name of influxDB user
- password - [required] password of influxDB user


Prometheus
----------
Prometheus is another time-series database supported by ASAB. 
Prometheus accesses ``asab/v1/metrics`` endpoint of ASAB ApiService. Thus, connecting ASAB to Prometheus requires APIService initialization.
ASAB metrics are presented to Prometheus in OpenMetrics standard format (https://openmetrics.io/). To satisfy the OpenMetrics format required by Prometheus, you should follow instructions below:

- Metrics names must fit regex ``[a-zA-Z:][a-zA-Z0-9_:]*``. (Any other characters are replaced by underscore. Leading underscores and numbers are stripped. These changes are proceeded without warning.)
- Metrics names MUST NOT end with “total” or “created”.
- Tags SHOULD contain items “unit” and “help” providing metadata to Prometheus.
- Values MUST be float or integer.

Example of your ASAB application configuration to enable Prometheus connection:

.. code:: ini

    [asab:metrics]
    target=prometheus

    [asab:metrics:prometheus]


Example of ``prometheus.yaml`` configuration file:

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



ASAB Metrics Interpretation
--------------------

To understand better how to interpret the ASAB metrics, you need to know a little bit more about the role of Metrics Service. 
Not only it creates new metrics, but Metrics Service also periodically collects their values and sends them to selected databases. 
Every 60 seconds in the application lifetime, Metrics Service gathers values of all ASAB metrics using :func:`flush` method implemented by each metric object.
All Counters (and metric types that inherit from :class:`Counter`) reset at this event to their initial values by default.
Interpretation of ASAB Counters is affected by their resetable nature. Even though they monotonously increase, reseting every minute gives them different meaning.
In a long term observation (that's how you most probably monitor the metric in time-series databases), these metrics count **events per minute**. 
Thus, resetable Counters are presented to Prometheus database as gauge type metrics. Set the `reset` argument to `False` when creating new Counter to disable Counter reseting.
This periodic "flush" cycle also causes 60s delay of metric propagation into supported time-series databases.


Web Requests Metrics
--------------------

There are default metrics in ASAB framework. :class:`WebService` class automatically provides with metrics counting web requests. 
There are 4 Counters quantifying requests to all ASAB endpoints. 

- `web_requests` - Counts requests to asab endpoints as events per minute.
- `web_requests_duration` - Counts total requests duration to asab endpoints per minute.
- `web_requests_duration_min` - Counts minimal request duration to asab endpoints per minute.
- `web_requests_duration_max` - Counts maximum request duration to asab endpoints per minute.


MetricsService
--------------

.. autoclass:: MetricsService
    :show-inheritance:

    .. automethod:: create_gauge

        Creates :class:`Gauge` object.

    .. automethod:: create_counter

        Creates :class:`Counter` object.

    .. automethod:: create_eps_counter

        Creates :class:`EPSCounter` object.

    .. automethod:: create_duty_cycle

        Creates :class:`DutyCycle` object.

    .. automethod:: create_agg_counter

        Creates :class:`AggregationCounter` object.



Metrics
-------

Gauge
------
.. autoclass:: Gauge
    :show-inheritance:

    Initial values must be provided when defining the metrics. Argument `init_values` is a dictionary with initial values and value names as keys.

    .. automethod:: set

    :param name: name of the value
    :param value: value itself


Counter
-------

.. autoclass:: Counter
    :show-inheritance:

    Initial values (`init_values` - dictionary of inital values with value names as keys) can be provided when initializing the metrics or added with :func:`add` or :func:`sub` methods.
    If reset is True, Counter resets every 60 seconds. 

    .. automethod:: add

    .. automethod:: sub


EPSCounter
----------
.. autoclass:: EPSCounter
    :show-inheritance:


DutyCycle
----------
.. autoclass:: DutyCycle
    :show-inheritance:

    To initialize DutyCycle, provide application loop (asab.Application.Loop) as this object tracks time of the application.


AggregationCounter
-------------------
.. autoclass:: AggregationCounter
    :show-inheritance:

    Values (their names and init_values) can be provided when initializing the metrics or added with :func:`set` method.
    :func:`add` and :func:`sub` methods are not implemented.

    .. automethod:: set

    Applies aggregation function on recent Counter value and value in argument and sets the result as new value of the Counter.

    :param str name: name of the value
    :param int value: value itself
    :param dict init-value: initial value, required when the counter name is not yet set up (i. e. by init_values in the constructor)


Metric
------
**Abstract class**

.. autoclass:: Metric
    :show-inheritance:

    :param str name: name of the metric
    :param dict tags: "host" tag is provided by default. "help" and "unit" tags are used as metadata by Prometheus database
        
    .. automethod:: flush

        Allows MetricsService to collect metrics values.

    .. automethod:: get_open_metric

        Parses metric data into OpenMetrics format and returns it as string. This format is required by Prometheus database.

    .. automethod:: rest_get

        Provides information about current metric state.







