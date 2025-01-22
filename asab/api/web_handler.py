import os

import aiohttp.web

from .. import Config
from ..web.rest import json_response
from ..web.auth import noauth, require_superuser
from ..web.tenant import allow_no_tenant


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


	@noauth
	@allow_no_tenant
	async def changelog(self, request):
		"""
		Get changelog file.
		---
		tags: ['asab.api']
		"""

		if self.ApiService.ChangeLog is None:
			return aiohttp.web.HTTPNotFound()

		with open(self.ApiService.ChangeLog, 'r') as f:
			result = f.read()

		return aiohttp.web.Response(text=result, content_type="text/markdown")


	@noauth
	@allow_no_tenant
	async def manifest(self, request):
		"""
		Get manifest of the ASAB service.

		The manifest is a JSON object loaded from `MANIFEST.json` file.
		The manifest contains the creation (build) time and the version of the ASAB service.
		The `MANIFEST.json` is produced during the creation of docker image by `asab-manifest.py` script.

		---
		tags: ['asab.api']

		responses:
			"200":
				description: Manifest of the application.
				content:
					application/json:
						schema:
							type: object
							properties:
								created_at:
									type: str
									example: 2024-12-10T15:49:37.14000
								version:
									type: str
									example: v24.50.01
		"""

		if self.ApiService.Manifest is None:
			return aiohttp.web.HTTPNotFound()

		return json_response(request, self.ApiService.Manifest)


	@require_superuser
	@allow_no_tenant
	async def environ(self, request):
		"""
		Get environment variables.

		Get JSON response containing the contents of the environment variables.

		---
		tags: ['asab.api']

		responses:
			"200":
				description: Environment variables.
				content:
					application/json:
						schema:
							type: object
							properties:
								LANG:
									type: str
									example: "en_GB.UTF-8"
								SHELL:
									type: str
									example: "/bin/zsh"
								HOME:
									type: str
									example: "/home/foobar"
		"""
		return json_response(request, dict(os.environ))


	@require_superuser
	@allow_no_tenant
	async def config(self, request):
		"""
		Get configuration of the service.

		Return configuration of the ASAB service in JSON format.

		**IMPORTANT: All passwords are erased.**

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

		responses:
			"200":
				description: Configuration of the service.
				content:
					application/json:
						schema:
							type: object
							example: {"general": {"config_file": "", "tick_period": "1", "uid": "", "gid": ""}, "asab:metrics": {"native_metrics": "true", "expiration": "60"}}
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
