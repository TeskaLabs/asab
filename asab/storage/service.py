import abc
import secrets
import hashlib

import asab

try:
	import cryptography.hazmat.primitives.ciphers
	import cryptography.hazmat.primitives.ciphers.algorithms
	import cryptography.hazmat.primitives.ciphers.modes
except ModuleNotFoundError:
	cryptography = None


ENCRYPTED_PREFIX = b"$aes-cbc$"


class StorageServiceABC(asab.Service):

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.WebhookURI = asab.Config.get("asab:storage:changestream", "webhook_uri", fallback="") or None
		self.WebhookAuth = asab.Config.get("asab:storage:changestream", "webhook_auth", fallback="") or None

		# Specify a non-empty AES key to enable AES encryption of selected fields
		self.AESKey = asab.Config.get("asab:storage", "aes_key", fallback="")
		if len(self.AESKey) > 0:
			if cryptography is None:
				raise ModuleNotFoundError(
					"You are using storage encryption without 'cryptography' installed. "
					"Please run 'pip install cryptography' "
					"or install asab with 'storage_encryption' optional dependency.")
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


	@abc.abstractmethod
	async def delete(self, collection: str, obj_id):
		pass


	def aes_encrypt(self, raw: bytes, iv: bytes = None) -> bytes:
		"""
		Take an array of bytes and encrypt it using AES-CBC.

		:param raw: The data to be encrypted
		:type raw: bytes
		:param iv: AES-CBC initialization vector, 16 bytes long. If left empty, a random 16-byte array will be used.
		:type iv: bytes
		:return: The encrypted data.
		"""
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8

		if self.AESKey is None:
			raise RuntimeError("No aes_key configured in asab:storage")

		if not isinstance(raw, bytes):
			if isinstance(raw, str):
				raise TypeError("String objects must be encoded before encryption")
			else:
				raise TypeError("Only 'bytes' objects can be encrypted")

		# Pad the text to fit the blocks
		pad_length = -len(raw) % block_size
		if pad_length != 0:
			raw = raw + b"\00" * pad_length

		if iv is None:
			iv = secrets.token_bytes(block_size)

		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self.AESKey)
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		encryptor = cipher.encryptor()
		encrypted = ENCRYPTED_PREFIX + iv + (encryptor.update(raw) + encryptor.finalize())
		return encrypted


	def aes_decrypt(self, encrypted: bytes) -> bytes:
		"""
		Decrypt encrypted data using AES-CBC.

		:param encrypted: The encrypted data to decrypt.
			It must start with b"$aes-cbc$" prefix, followed by one-block-long initialization vector.
		:type encrypted: bytes
		:return: The decrypted data.
		"""
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8

		if self.AESKey is None:
			raise RuntimeError("No aes_key configured in asab:storage")

		if not isinstance(encrypted, bytes):
			raise TypeError("Only values of type 'bytes' can be decrypted")

		# Strip the prefix
		if not encrypted.startswith(ENCRYPTED_PREFIX):
			raise ValueError("Encrypted data must start with {!r} prefix".format(ENCRYPTED_PREFIX))
		encrypted = encrypted[len(ENCRYPTED_PREFIX):]

		# Separate the initialization vector
		iv, encrypted = encrypted[:block_size], encrypted[block_size:]

		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self.AESKey)
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		decryptor = cipher.decryptor()
		raw = decryptor.update(encrypted) + decryptor.finalize()

		# Strip padding
		raw = raw.rstrip(b"\x00")
		return raw
