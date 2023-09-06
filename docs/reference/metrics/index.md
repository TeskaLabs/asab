---
title: Metrics
---

# Metrics

Metrics document the state of the application in a timescale manner. 
For further analysis, connect your ASAB application to a time-series
database. [Influx](https://www.influxdata.com/) and
[Prometheus](https://prometheus.io/) are supported.

Learn how to [monitor](./monitoring.md) [built-in metrics](./built_ins.md) or [create](./create_metrics.md) your own.
There is a list of [metric types](./metrics_types.md) enabling you to monitor various situations.
Be sure you are familiar with the [interpretation](./interpretation.md) of metrics in ASAB when analyzing the data.
[Tags](./tags.md) will help you to filter and group time-series datasets.

To enable metrics functionality in ASAB, add metrics module to your application.

!!! example

	``` python
	class MyApplication(asab.Application):
		async def initialize(self):
			from asab.metrics import Module
			self.add_module(Module)
	```