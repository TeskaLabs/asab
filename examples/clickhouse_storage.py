import time

import asab
import asab.storage


asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'clickhouse',
			'host': 'localhost',
		}
	}
)


class MyApplication(asab.Application):


	async def initialize(self):
		self.add_module(asab.storage.Module)


	async def main(self):
		storage = self.get_service("asab.StorageService")

		storage.set_database("lmio")
		storage.set_table("logs", "`@timestamp` Int64, `log.original` String")
		storage.clear()

		event = {
			"@timestamp": int(time.time()),
			"log.original": "log message",
		}

		for i in range(0, storage.BulkSize):
			storage.insert(event)

		print("INSERTED DATA: ------")
		data = storage.list()

		for n, item in enumerate(data):
			print(n + 1, item)

		print("---------------------")

		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
