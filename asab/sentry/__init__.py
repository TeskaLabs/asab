from .service import SentryService
from ..config import Config

Config.add_defaults(
	{
		"sentry": {
			"data_source_name": "",
			"environment": "not specified",
			"traces_sample_rate": 1.0,
		},

		"sentry:logging": {
			"breadcrumbs": "info",
			"events": "warning"
		}
	}
)

__all__ = ["SentryService"]
