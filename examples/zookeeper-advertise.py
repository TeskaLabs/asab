import asab
import asab.api
import asab.zookeeper


# Advertisement through ApiService requires two configuration sections - `web` and `zookeeper`
asab.Config.add_defaults(
	{
		"web": {
			"listen": "0.0.0.0 8088",
		},
		"zookeeper": {
			"servers": "zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181",
			"path": "asab"
		},
	}
)


class MockApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Loading the web service module
		self.add_module(asab.web.Module)
		self.WebService = self.get_service("asab.WebService")

		# Load a zookeeper service module
		self.add_module(asab.zookeeper.Module)
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")

		# Initialize API service
		self.ApiService = asab.api.ApiService(self)

		# Introduce Web and ZooKeeper to API Service
		self.ApiService.initialize_web()
		self.ApiService.initialize_zookeeper()


if __name__ == '__main__':
	app = MockApplication()
	app.run()
