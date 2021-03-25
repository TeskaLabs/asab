import asab.web.rest
import asab.pyppeteer

asab.Config.add_defaults({
	"general": {
		"var_dir": "examples"
	}
})


class PyppeteerHandler(object):
	def __init__(self, app, pyppeteer_service):
		self.PyppeteerService = pyppeteer_service
		web_app = app.WebContainer.WebApp
		web_app.router.add_put(r"/screenshot_png", self.screenshot_png)

	@asab.web.rest.json_schema_handler({
		'type': 'object',
		'properties': {
			'url': {'type': 'string'},
			'file_name': {'type': 'string'},
		}})
	async def screenshot_png(self, request, *, json_data):
		url = json_data["url"]
		file_name = json_data.get("file_name")
		success = await self.PyppeteerService.capture_screenshot(url, file_name)
		if not success:
			return asab.web.rest.json_response(
				request,
				data={
					"result": "FAILED"
				}
			)
		return asab.web.rest.json_response(
			request,
			data={
				"result": "OK"
			}
		)


class ScreenshotApplication(asab.Application):
	"""
	ScreenshotApplication
	"""

	def __init__(self):
		super().__init__()
		# Loading the web service module
		self.add_module(asab.web.Module)
		# Locate web service
		self.WebService = self.get_service("asab.WebService")
		self.WebContainer = asab.web.WebContainer(
			self.WebService,
			"example:pyppeteer",
			config={"listen": "0.0.0.0 8083"}
		)
		self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)

		self.PyppeteerService = asab.pyppeteer.PyppeteerService(self)
		self.PyppeteerHandler = PyppeteerHandler(self, self.PyppeteerService)


if __name__ == "__main__":
	app = ScreenshotApplication()
	app.run()
