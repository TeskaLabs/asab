import logging

import clickhouse_driver

from .service import StorageServiceABC
from ..config import Config

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		"asab:storage": {
			"host": "",
			"port": "",
			"user": "",
			"password": "",
			"bulk_size": 1000,
		}
	}
)


class StorageService(StorageServiceABC):

	def __init__(self, app, service_name, config_section_name='asab:storage'):
		super().__init__(app, service_name)
		self.Loop = app.Loop

		host = Config.get(config_section_name, 'host')
		user = Config.get(config_section_name, 'user')
		password = Config.get(config_section_name, 'password')

		if len(user) == 0:
			self.Client = clickhouse_driver.Client(
				host=host
			)

		else:
			self.Client = clickhouse_driver.Client(
				host=host, user=user, password=password
			)

		self.BulkSize = Config.getint(config_section_name, 'bulk_size')
		self.Bulk = []
		self.BulkLen = 0
		self.Database = None
		self.Table = None
		self.Schema = None


	def set_database(self, database):
		self.Database = database
		self.Client.execute('CREATE DATABASE IF NOT EXISTS {}'.format(database))


	def set_table(self, table, schema):
		self.Table = table
		self.Schema = schema
		self.Client.execute("CREATE TABLE IF NOT EXISTS {}.{} ({}) ENGINE = Memory".format(
			self.Database, table, schema)
		)


	def insert(self, values):
		self.Bulk.append(values)
		self.BulkLen += 1

		if self.BulkLen >= self.BulkSize:
			self._insert_bulk_to_database()
			self.Bulk = []
			self.BulkLen = 0


	def _insert_bulk_to_database(self):
		self.Client.execute('INSERT INTO {}.{} VALUES'.format(
			self.Database, self.Table), self.Bulk)


	def list(self):
		data = self.Client.execute('SELECT * FROM {}.{}'.format(
			self.Database, self.Table)
		)

		return data


	def clear(self):
		self.Client.execute('ALTER TABLE {}.{} DELETE WHERE 1'.format(
			self.Database, self.Table)
		)


	# TODO: To be implemented?
	def upsertor(self, collection: str, obj_id=None, version: int = 0):
		pass


	async def get(self, collection: str, obj_id, decrypt=None) -> dict:
		pass


	async def get_by(self, collection: str, key: str, value, decrypt=None):
		pass


	async def delete(self, collection: str, obj_id):
		pass
