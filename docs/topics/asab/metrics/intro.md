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

	1. Import asab.metrics Module and add it to the application.
	2. Then, you can localize MetricsService.
	3. Use MetricsService to intialize the counter.


See the full example here:
<https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py>

See reference here (TODO link)

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

`Counter`, `AggregationCounter` and `Histogram` come also in variants
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
resettable Counters are presented to Prometheus database as gauge-type
metrics. Set the `reset` argument to `False`
when creating a new Counter to disable Counter resetting. This periodic
"flush" cycle also causes 60s delay of metric propagation into
supported time-series databases.
Please, see the Timestamp section explaining the origin of a timestamp in each metric record.

## Initial Values

You can initiate your metric instance **with or without initial values**.
Initial values are always present and presented to databases even without a single event changing the metric values.
You will always find a pair of value name and its value in resulting dataset.
Values (name and value pairs) added during runtime last only 60 s.
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



