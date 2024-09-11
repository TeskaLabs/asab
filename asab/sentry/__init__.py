from .service import SentryService
from ..config import Config

Config.add_defaults(
	{
		"sentry": {
			"data_source_name": "",
			"environment": "not specified",
			"traces_sample_rate": 0,  # https://docs.sentry.io/platforms/python/configuration/sampling/#configuring-the-transaction-sample-rate
		},

		"sentry:logging": {
			"breadcrumbs": "info",
			"events": "error"
		}
	}
)

__all__ = ["SentryService"]
