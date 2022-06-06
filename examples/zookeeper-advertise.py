import asab
import asab.api
import asab.zookeeper


class MyApplication(asab.Application):

	def __init__(self):
		super().__init__(modules=[asab.web.Module, asab.zookeeper.Module])

		# Locate a Web Service
		self.WebService = self.get_service("asab.WebService")

		# Locate a ZooKeeper Service
		self.ZooKeeperService = self.get_service("asab.ZooKeeperService")

		# Initialize API service
		self.ApiService = asab.api.ApiService(self)

		# Introduce Web and ZooKeeper to API Service
		self.ApiService.initialize_web()
		self.ApiService.initialize_zookeeper()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
