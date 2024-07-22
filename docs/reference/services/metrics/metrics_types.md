# Types of Metrics

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


::: asab.metrics.metrics.Gauge
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.Counter
    handler: python
    options:
      members:
        - add
		- sub
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.EPSCounter
    handler: python
    options:
      members:
        - add
		- sub
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.DutyCycle
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.AggregationCounter
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.Histogram
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.CounterWithDynamicTags
    handler: python
    options:
      members:
        - add
		- sub
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.AggregationCounterWithDynamicTags
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3


::: asab.metrics.metrics.HistogramWithDynamicTags
    handler: python
    options:
      members:
        - set
      show_root_heading: true
      show_source: true
	  heading_level: 3