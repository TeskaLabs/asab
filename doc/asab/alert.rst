Alert Service
=============

ASAB Alert Service implements several targets for alerts created in your application.
Everything you need to do in your code is to import the service and trigger the alert:


.. code:: python 

    class MyApplication(asab.Application):
        async def initialize(self):
            from asab.alert import AlertService
            self.AlertService = AlertService(self)
            self.AlertService.trigger(
                tenant_id="my-tenant",
                alert_cls="my-class",
                alert_id="deduplication-id01",
                title="Something went wrong.",
                detail={
                    "example1": "additional-info",
                    "example2": "additional-info",
                },
            )

    if __name__ == '__main__':
        app = MyApplication()
        app.run()


The code itself is not enough. The alert is produced only when the specific target is configured.
Up to now there are two possible target systems for the alerts:
- Opsgenie - https://www.atlassian.com/software/opsgenie
- PagerDuty - https://events.pagerduty.com


Opsgenie
--------

*myapplication.conf*

.. code::

	[asab:alert:opsgenie]
	api_key=my-api-key-123456
	tags=my-tag, my-application
	url=https://api.eu.opsgenie.com  # this is default value


PagerDuty
---------

*myapplication.conf*

.. code::

	[asab:alert:pagerduty]
	api_key=w_8PcNuhHa-y3xYdmc1x
	integration_key=f
	url=https://events.pagerduty.com  # this is default value

	