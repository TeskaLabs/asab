Alert Service
=============

Integrate ASAB Application with alert managers.

There are currently two possible target systems for the alerts
available:

-   Opsgenie - <https://www.atlassian.com/software/opsgenie>
-   PagerDuty - <https://events.pagerduty.com>

Everything you need to do is to import the service, trigger the alert
and specify the target in the **configuration**.

``` {.python}
class MyApplication(asab.Application):
    async def initialize(self):
        from asab.alert import AlertService
        self.AlertService = AlertService(self)
        self.AlertService.trigger(
            source="my-tenant",
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
```

Opsgenie
--------

-   Create an account at Opsgenie.
-   In your Opsgenie account, create a new **Team**.
-   Add integration to your Team - choose **API**.
-   API Key will be generated for you.

*myapplication.conf*

``` {.}
[asab:alert:opsgenie]
api_key=my-api-key
tags=my-tag, my-application
url=https://api.eu.opsgenie.com  # this is default value
```

PagerDuty
---------

-   Create an account at PagerDuty.
-   In your PagerDuty account, generate **Api Key** (Integrations \>
    Developer Tools \> Api Access Keys).
-   Create a new Service in Service Directory and add integration in the
    Integrations folder.
-   Choose **Events API V2**. An **Integration Key** will be generated
    for you.

*myapplication.conf*

``` {.}
[asab:alert:pagerduty]
api_key=my-api-key
integration_key=my-integration-key
url=https://events.pagerduty.com  # this is default value
```

De-duplication
--------------

[alert\_id]{.title-ref} argument serves as a de-duplication ID for the
third-party services. It enables the grouping of alerts and prevents
noise. More about alert grouping:

-   Opsgenie:
    <https://support.atlassian.com/opsgenie/docs/what-is-alert-de-duplication/>
-   PagerDuty:
    <https://support.pagerduty.com/docs/intelligent-alert-grouping>
