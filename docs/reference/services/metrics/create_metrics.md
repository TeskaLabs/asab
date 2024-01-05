# Create new metrics

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
	3. Use MetricsService to initialize the counter.


See the full example [here](https://github.com/TeskaLabs/asab/blob/master/examples/metrics.py).

!!! warning

	All methods that create new metrics objects can be found in the Metrics
	Service reference. You should never initiate a new metrics object on its
	own, but always through Metrics Service. Metris initialization is meant
	to be done in the init time of your application and **should not be done
	during runtime**.


::: asab.metrics.service.MetricsService
    handler: python
    options:
      members:
        - create_gauge
        - create_counter
        - create_eps_counter
        - create_duty_cycle
        - create_aggregation_counter
        - create_histogram
      show_root_heading: true
      show_source: false
	  heading_level: 3