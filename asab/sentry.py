import sentry_sdk
import sentry_sdk.integrations.aiohttp
import sentry_sdk.integrations.asyncio
import sentry_sdk.integrations.logging

import asab


class SentryContainer(asab.Configurable):

	ConfigDefaults = {
		"dsn": "",
		"traces_sample_rate": 1.0,
		"environment": "testing"
	}

	def __init__(self, config_section_name="sentry", config=None):
		super().__init__(config_section_name, config)

		self.Dsn = self.Config.get("dsn")
		self.Environment = self.Config.get("environment")
		self.TracesSampleRate = self.Config.get("traces_sample_rate")

		sentry_sdk.init(
			dsn=self.Dsn,
			integrations=[
				sentry_sdk.integrations.aiohttp.AioHttpIntegration,
				sentry_sdk.integrations.asyncio.AsyncioIntegration,
				sentry_sdk.integrations.logging.LoggingIntegration,
			],
			traces_sample_rate=self.TracesSampleRate,
		)
