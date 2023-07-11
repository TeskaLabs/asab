---
author: "Anton\xEDn"
commit: abb1e5ad150a5f5be46f333bfeabd2b8a82cc971
date: 2022-07-28 12:45:35+02:00
title: Config geturl

---

!!! example

	```python title=config_geturl.py linenums="1"
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
			"mongodb": "mongodb://LOCALHOST:27017/coolDB/",  # Has a trailing slash
			"github": "github.com",  # Has no scheme
		}
	})
	
	
	class MyApplication(asab.Application):
	
		def __init__(self):
			super().__init__()
	
			# Two ways of obtaining the URL
			self.UrlsTeskalabs = asab.Config["urls"].geturl("teskalabs", scheme="https")
			self.UrlsGoogle = asab.Config.geturl("urls", "google", scheme=None)
	
			self.UrlsMongo = asab.Config["urls"].geturl("mongodb", scheme="mongodb")
			self.UrlsGithub = asab.Config.geturl("urls", "github", scheme=None)
	
			# You can also use a tuple in the scheme parameter
			self.UrlsMongoTuple = asab.Config["urls"].geturl("mongodb", scheme=("https", "mongodb"))
			self.UrlsTeskalabsTuple = asab.Config["urls"].geturl("teskalabs", scheme=("https", "mongodb"))
	
	
		# This would throw a Error, because the URL in config has no scheme
		# self.UrlsGithub = asab.Config.geturl("urls", "github", scheme="https")
	
	
		async def main(self):
			L.warning("Did you know the url for TeskaLabs is {}".format(self.UrlsTeskalabs))
			L.warning("Did you know the url for Google is {}".format(self.UrlsGoogle))
			L.warning("Checkout my MongoDB {} Oh wait you can't :(️".format(self.UrlsMongo))
			L.warning("Github: {}".format(self.UrlsGithub))
			L.warning("MongoDB using a tuple scheme: {}".format(self.UrlsMongoTuple))
			L.warning("TeskaLabs using a tuple scheme: {}".format(self.UrlsTeskalabsTuple))
	
			L.warning("Stopping the application.")
			self.stop()
	
	
	if __name__ == "__main__":
		app = MyApplication()
		app.run()
	
	```
