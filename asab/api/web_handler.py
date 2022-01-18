import os
import asab.web
import aiohttp.web


class APIWebHandler(object):
    def __init__(self, app, webapp, log_handler):
        self.App = app

        # Add routes
        webapp.router.add_get("/asab/v1/environ", self.environ)
        webapp.router.add_get("/asab/v1/config", self.config)

        webapp.router.add_get("/asab/v1/logs", log_handler.get_logs)
        webapp.router.add_get("/asab/v1/logws", log_handler.ws)

        webapp.router.add_get("/asab/v1/changelog", self.changelog)

        webapp.router.add_get("/asab/v1/metrics", self.metrics)

    async def metrics(self, request):
        metrics_service = self.App.get_service("asab.MetricsService")
        if metrics_service is None:
            raise RuntimeError("asab.MetricsService is not available")

        from asab.metrics.prometheus import to_openmetrics

        text = to_openmetrics(metrics_service)

        return aiohttp.web.Response(
            text=text,
            content_type="text/plain",
            charset="utf-8",
        )

    async def changelog(self, request):
        path = asab.Config.get("general", "changelog_path")
        if not os.path.isfile(path):
            if os.path.isfile("/CHANGELOG.md"):
                path = "/CHANGELOG.md"
            elif os.path.isfile("CHANGELOG.md"):
                path = "CHANGELOG.md"
            else:
                return aiohttp.web.HTTPNotFound()

        with open(path) as f:
            result = f.read()

        return aiohttp.web.Response(text=result, content_type="text/markdown")

    async def environ(self, request):
        return asab.web.rest.json_response(request, dict(os.environ))

    async def config(self, request):
        # Copy the config and erase all passwords
        result = {}
        for section in asab.Config.sections():
            result[section] = {}
            # Access items in the raw mode (they are not interpolated)
            for option, value in asab.Config.items(section, raw=True):
                if section == "passwords":
                    result[section][option] = "***"
                else:
                    result[section][option] = value
        return asab.web.rest.json_response(request, result)
