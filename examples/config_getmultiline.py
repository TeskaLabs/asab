#!/usr/bin/env python3
import asab
import logging

#

L = logging.getLogger(__name__)

#

asab.Config.read_string(
	"""
	[places]
	visited:
			Praha
			Brno
			Ústí nad Labem
	"""
)


class MyApplication(asab.Application):

	async def main(self):
		visited = asab.Config.getmultiline("places", "visited")
		unvisited = asab.Config.getmultiline("places", "unvisited", fallback=[])
		nonexisting = asab.Config.getmultiline("places", "nonexisting", fallback=["Gottwaldov"])
		L.log(asab.LOG_NOTICE, "Places I've already visited: {}".format(visited))
		L.log(asab.LOG_NOTICE, "Places I want to visit: {}".format(unvisited))
		L.log(asab.LOG_NOTICE, "Places that don't exist: {}".format(nonexisting))
		self.stop()


if __name__ == "__main__":
	app = MyApplication()
	app.run()
