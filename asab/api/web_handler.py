import os

import aiohttp.web

from .. import Config
from ..web.rest import json_response


class APIWebHandler(object):

	def __init__(self, api_svc, webapp, log_handler):
		self.App = api_svc.App
		self.ApiService = api_svc

		# Add routes
		webapp.router.add_get("/asab/v1/environ", self.environ)
		webapp.router.add_get("/asab/v1/config", self.config)

		webapp.router.add_get("/asab/v1/logs", log_handler.get_logs)
		webapp.router.add_get("/asab/v1/logws", log_handler.ws)

		webapp.router.add_get("/asab/v1/changelog", self.changelog)
		webapp.router.add_get("/asab/v1/manifest", self.manifest)


	async def changelog(self, request):
		"""
		It returns a change log file.
		---
		tags: ['asab.api']
		"""

		if self.ApiService.ChangeLog is None:
			return aiohttp.web.HTTPNotFound()

		with open(self.ApiService.ChangeLog, 'r') as f:
			result = f.read()

		return aiohttp.web.Response(text=result, content_type="text/markdown")


	async def manifest(self, request):
		"""
		It returns the manifest of the ASAB service.

		THe manifest is a JSON object loaded from `MANIFEST.json` file.
		The manifest contains the creation (build) time and the version of the ASAB service.
		The `MANIFEST.json` is produced during the creation of docker image by `asab-manifest.py` script.

		Example of `MANIFEST.json`:

		```
		{
			'created_at': 2022-03-21T15:49:37.14000,
			'version' :v22.9-4
		}
		```

		---
		tags: ['asab.api']
		"""

		if self.ApiService.Manifest is None:
			return aiohttp.web.HTTPNotFound()

		return json_response(request, self.ApiService.Manifest)


	async def environ(self, request):
		"""
		It returns a JSON response containing the contents of the environment variables.

		Example:

		```
		{
			"LANG": "en_GB.UTF-8",
			"SHELL": "/bin/zsh",
			"HOME": "/home/foobar",
		}

		```

		---
		tags: ['asab.api']
		"""
		return json_response(request, dict(os.environ))


	async def config(self, request):
		"""
		It returns the JSON with the config of the ASAB service.

		IMPORTANT: All passwords are erased.

		Example:

		```
		{
			"general": {
				"config_file": "",
				"tick_period": "1",
				"uid": "",
				"gid": ""
			},
			"asab:metrics": {
				"native_metrics": "true",
				"expiration": "60"
			}
		}
		```

		---
		tags: ['asab.api']
		"""

		# Copy the config and erase all passwords
		result = {}
		for section in Config.sections():
			result[section] = {}
			# Access items in the raw mode (they are not interpolated)
			for option, value in Config.items(section, raw=True):
				if section == "passwords":
					result[section][option] = "***"
				else:
					result[section][option] = value
		return json_response(request, result)
