.. currentmodule:: asab.metrics

Metrics service
===============
Metrics document desired situation in a timescale manner. Default ASAB metrics counting web requests are provided together with :class:`WebService`.
For further analysis, connect your ASAB application with a time-series database. ASAB supports Influx and Prometheus databases.

TODO:  
- prolinkovat na WebService
- odkázat na example

Metrics types
-------------
All metrics types inherit from :class:`Metric` class.

- :class:`Gauge` enables to set a distinct value at each timepoint. 
- :class:`Counter` allows to add or substract a value from total count. All Counters (and metric types that inherit from them) are flushed by MetricsService every 60s by default. In a long term observation, these metrics count **events per minute**. Reseting can be disabled.
- Event per Second Counter (:class:`EPSCounter`) divides all values by delta time. 
- :class:`DutyCycle` https://en.wikipedia.org/wiki/Duty_cycle (TODO: já vlastně nevím, co to dělá)
- :class:`AggregationCounter` allows to set new value based on aggregation function. :func:`max` function is default.

MetricsService
--------------

.. note::
    Flush


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

Prometheus
----------
When using Prometheus, metrics name must fit regex ``[a-zA-Z:][a-zA-Z0-9_:]*`` . Any other characters are replaced by underscore. Leading underscores and numbers are stripped. These changes are proceeded without warning.
- Metric Name MUST NOT end with “total” or “created”
- Tags SHOULD contain items “unit” and “help”
- Values MUST be float or int

Reference
=========

Metrics types
-------------

Gauge
------
.. autoclass:: Gauge
    :show-inheritance:

    Values (init_values) must be provided when initializing the metrics. 

    :param str name: name of the metric
    :param dict tags: provide "help" and "unit" metadata used by Prometheus database
    :param dict init_values: dict of inital values with value names as keys

    .. automethod:: set

    :param name: name of the value
    :param value: value itself (int/float)


Counter
-------

.. autoclass:: Counter
    :show-inheritance:

    Values (their names and init_values) can be provided when initializing the metrics or added with :func:`add` or :func:`sub` methods.

    :param str name: name of the metric
    :param dict tags: provide "help" and "unit" metadata used by Prometheus database
    :param dict init_values: dict of inital values with value names as keys
    :param bool reset: if True, Counter resets when flushed

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

    :param loop:
    :param str name: name of the metric
    :param dict tags:
    :param dict init_values:



AggregationCounter
-------------------
.. autoclass:: AggregationCounter
    :show-inheritance:

    Values (their names and init_values) can be provided when initializing the metrics or added with :func:`set` method.
    :func:`add` and :func:`sub` methods are not implemented.

    .. automethod:: set

    Applies aggregation function on recent Counter value and value in argument and sets the result as new value of the Counter.

        :param name: name of the value
        :param value: value itself (int/float)
        :param init-value: initial value, required when the counter name is not yet set up (i. e. by init_values in the constructor)


Metric
------
Abstract class

.. autoclass:: Metric(name, tags)
    :show-inheritance:

    :param str name: ame of the metric
    :param dict tags: provide "help" and "unit" metadata used by Prometheus database
        
    .. automethod:: flush

        Allows MetricsService to collect metrics values and present them to time-series databases.

    .. automethod:: get_open_metric

        To return metric state in OpenMetrics format https://openmetrics.io/ .


    .. automethod:: rest_get

        Returns dict with current metric state.






