import abc
import typing

import asab

import hashlib
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes


class StorageServiceABC(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.WebhookURI = asab.Config.get("asab:storage:changestream", "webhook_uri", fallback="") or None
		self.WebhookAuth = asab.Config.get("asab:storage:changestream", "webhook_auth", fallback="") or None
		self.AESKey = asab.Config.get("asab:storage", "aes_key", fallback="") or None
		if self.AESKey is not None:
			self.AESKey = hashlib.sha256(self.AESKey.encode("utf-8")).digest()


	@abc.abstractmethod
	def upsertor(self, collection: str, obj_id=None, version: int = 0):
		'''
		If updating an existing object, please specify its `obj_id` and also `version` that you need to read from a storage upfront.
		If `obj_id` is None, we assume that you want to insert a new object and generate its new `obj_id`, `version` should be set to 0 (default) in that case.
		If you want to insert a new object with a specific `obj_id`, specify `obj_id` and set a version to 0.
			- If there will be a colliding object already stored in a storage, `execute()` method will fail on `DuplicateError`.

		:param collection: Name of collection to work with
		:param obj_id: Primary identification of an object in the storage (e.g. primary key)
		:param version: Specify a current version of the object and hence prevent byzantine faults. \
						You should always read the version from the storage upfront, prior using an upsertor. \
						That creates a soft lock on the record. It means that if the object is updated by other \
						component in meanwhile, your upsertor will fail and you should retry the whole operation. \
						The new objects should have a `version` set to 0.
		'''
		pass


	@abc.abstractmethod
	async def get(self, collection: str, obj_id, decrypt=None) -> dict:
		"""
		Get object from collection

		:param collection: Collection to get from
		:param obj_id: Object identification
		:param decrypt: Set of fields to decrypt
		:return: The object retrieved from a storage

		Raises:
			KeyError: If `obj_id` not found in `collection`
		"""
		pass


	@abc.abstractmethod
	async def get_by(self, collection: str, key: str, value, decrypt=None):
		"""
		Get object from collection by its key/value

		:param collection: Collection to get from
		:param key: Key to filter on
		:param value: Value to filter on
		:param decrypt: Set of fields to decrypt
		:return: The object retrieved from a storage

		Raises:
			KeyError: If object {key: value} not found in `collection`
		"""
		pass


	async def get_by_encrypted(self, collection: str, key: str, value, decrypt=None):
		"""
		Get object from collection by its key and encrypted value

		:param collection: Collection to get from
		:param key: Key to filter on
		:param value: Value to encrypt and filter on
		:param decrypt: Set of fields to decrypt
		:return: The object retrieved from a storage

		Raises:
			KeyError: If object {key: value} not found in `collection`
		"""
		return await self.get_by(collection, key, self.aes_encrypt(value), decrypt)


	@abc.abstractmethod
	async def delete(self, collection: str, obj_id):
		pass


	def aes_encrypt(self, raw: typing.Union[str, bytes]):
		"""
		Take a string or bytes and encrypt it using AES-CBC.

		:param raw: The data to be encrypted
		:type raw: typing.Union[str, bytes]
		:return: The encrypted data.
		"""
		assert self.AESKey is not None
		if isinstance(raw, str):
			raw = raw.encode("utf-8")
		assert isinstance(raw, bytes)
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8
		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self.AESKey)
		iv, token = raw[:block_size], raw[block_size:]
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		encryptor = cipher.encryptor()
		encrypted = iv + (encryptor.update(token) + encryptor.finalize())
		return encrypted


	def aes_decrypt(self, encrypted: bytes):
		"""
		Decrypt encrypted data using AES-CBC.

		:param encrypted: The encrypted data to decrypt
		:type encrypted: bytes
		:return: The decrypted data.
		"""
		assert self.AESKey is not None
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8
		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self.AESKey)
		iv, token = encrypted[:block_size], encrypted[block_size:]
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		decryptor = cipher.decryptor()
		raw = iv + (decryptor.update(token) + decryptor.finalize())
		return raw
