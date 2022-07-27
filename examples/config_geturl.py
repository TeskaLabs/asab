#!/usr/bin/env python3
import logging

import asab
import asab.utils

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults({
	"urls": {
		"teskalabs": "https://www.teskalabs.com/",  # Has a trailing slash
		"google": " https://www.google.com/ ",  # Has leading and trailing whitespace and a trailing slash
		"mongodb": "mongodb://LOCALHOST:27017/coolDB/",  # Has a trailing slash, and has some capitals
		"github": "github.com",  # Has no schema
	}
})


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Two ways of obtaining the URL
		self.UrlsTeskalabs = asab.Config["urls"].geturl("teskalabs", schema="https")
		self.UrlsGoogle = asab.Config.geturl("urls", "google", schema=None)

		self.UrlsMongo = asab.Config["urls"].geturl("mongodb", schema="mongodb")
		self.UrlsGithub = asab.Config.geturl("urls", "github", schema=None)

		self.UrlsMongoTuple = asab.Config["urls"].geturl("mongodb", schema=("https", "mongodb"))
		self.UrlsTeskalabsTuple = asab.Config["urls"].geturl("teskalabs", schema=("https", "mongodb"))


	# This would throw a Error, because the URL in config has no schema
	# self.UrlsGithub = asab.Config.geturl("urls", "github", schema="https")


	async def main(self):
		L.warning("Did you know the url for TeskaLabs is {}".format(self.UrlsTeskalabs))
		L.warning("Did you know the url for Google is {}".format(self.UrlsGoogle))
		L.warning("Checkout my MongoDB {} Oh wait you can't :(️".format(self.UrlsMongo))
		L.warning("Github: {}".format(self.UrlsGithub))
		L.warning("MongoDB using a tuple schema: {}".format(self.UrlsMongoTuple))
		L.warning("TeskaLabs using a tuple schema: {}".format(self.UrlsTeskalabsTuple))

		L.warning("Stopping the application.")
		self.stop()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
