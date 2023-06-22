import abc
import secrets
import hashlib
import logging
import asab
import re

try:
	import cryptography.hazmat.primitives.ciphers
	import cryptography.hazmat.primitives.ciphers.algorithms
	import cryptography.hazmat.primitives.ciphers.modes
except ModuleNotFoundError:
	cryptography = None

#

L = logging.getLogger(__name__)

#


ENCRYPTED_PREFIX = b"$aes-cbc$"


class StorageServiceABC(asab.Service):
	"""
	An abstract class for the Storage Service.

	"""

	def __init__(self, app, service_name):
		super().__init__(app, service_name)
		self.WebhookURIs = asab.Config.get("asab:storage:changestream", "webhook_uri", fallback="") or None
		if self.WebhookURIs is not None:
			self.WebhookURIs = [uri for uri in re.split(r"\s+", self.WebhookURIs) if len(uri) > 0]
			try:
				self.ProactorService = app.get_service("asab.ProactorService")
			except KeyError as e:
				raise Exception("Storage webhooks require ProactorService") from e
		self.WebhookAuth = asab.Config.get("asab:storage:changestream", "webhook_auth", fallback="") or None

		# Specify a non-empty AES key to enable AES encryption of selected fields
		self._AESKey = asab.Config.get("asab:storage", "aes_key", fallback="")
		if len(self._AESKey) > 0:
			if cryptography is None:
				raise ModuleNotFoundError(
					"You are using storage encryption without 'cryptography' installed. "
					"Please run 'pip install cryptography' "
					"or install asab with 'storage_encryption' optional dependency.")
			self._AESKey = hashlib.sha256(self._AESKey.encode("utf-8")).digest()
		else:
			self._AESKey = None


	@abc.abstractmethod
	def upsertor(self, collection: str, obj_id=None, version: int = 0) -> None:
		"""
		Create an upsertor object for the specified collection.

		If updating an existing object, please specify its `obj_id` and also `version` that you need to read from a storage upfront.
		If `obj_id` is None, we assume that you want to insert a new object and generate its new `obj_id`, `version` should be set to 0 (default) in that case.
		If you want to insert a new object with a specific `obj_id`, specify `obj_id` and set a version to 0.
			- If there will be a colliding object already stored in a storage, `execute()` method will fail on `DuplicateError`.

		Args:

		collection (str): Name of collection to work with
		obj_id: Primary identification of an object in the storage (e.g. primary key)
		version (int): Specify a current version of the object and hence prevent byzantine faults. \
		You should always read the version from the storage upfront, prior using an upsertor. \
		That creates a soft lock on the record. It means that if the object is updated by other \
		component in meanwhile, your upsertor will fail and you should retry the whole operation. \
		The new objects should have a `version` set to 0.
		"""
		pass


	@abc.abstractmethod
	async def get(self, collection: str, obj_id, decrypt=None) -> dict:
		"""
		Get object from collection by its ID.

		Args:
			collection (str): Collection to get from.
			obj_id: Object identification.
			decrypt (bool): Set of fields to decrypt.

		Returns:
			The object retrieved from a storage.

		Raises:
			KeyError: Raised if `obj_id` is not found in `collection`.
		"""
		pass


	@abc.abstractmethod
	async def get_by(self, collection: str, key: str, value, decrypt=None) -> dict:
		"""
		Get object from collection by its key and value.

		Args:
			collection: Collection to get from
			key: Key to filter on
			value: Value to filter on
			decrypt: Set of fields to decrypt

		Returns:
			The object retrieved from a storage.

		Raises:
			KeyError: If object {key: value} not found in `collection`
		"""
		pass


	@abc.abstractmethod
	async def delete(self, collection: str, obj_id):
		"""
		Delete object from collection.

		Args:
			collection: Collection to get from
			obj_id: Object identification

		Returns:
			ID of the deleted object.

		Raises:
			KeyError: Raised when obj_id cannot be found in collection.
		"""
		pass


	def aes_encrypt(self, raw: bytes, iv: bytes = None) -> bytes:
		"""
		Take an array of bytes and encrypt it using AES-CBC.

		Args:
			raw: The data to be encrypted.
			iv: AES-CBC initialization vector, 16 bytes long. If left empty, a random 16-byte array will be used.

		Returns:
			The encrypted data.

		Raises:
			TypeError: The data are not in binary format.
		"""
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8

		if self._AESKey is None:
			raise RuntimeError(
				"No aes_key specified in asab:storage configuration. "
				"If you want to use encryption, specify a non-empty aes_key."
			)

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

		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self._AESKey)
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		encryptor = cipher.encryptor()
		encrypted = ENCRYPTED_PREFIX + iv + (encryptor.update(raw) + encryptor.finalize())
		return encrypted


	def aes_decrypt(self, encrypted: bytes) -> bytes:
		"""
		Decrypt encrypted data using AES-CBC.

		Args:
			encrypted: The encrypted data to decrypt. It must start with b"$aes-cbc$" prefix, followed by one-block-long initialization vector.

		Returns:
			The decrypted data.
		"""
		block_size = cryptography.hazmat.primitives.ciphers.algorithms.AES.block_size // 8

		if self._AESKey is None:
			raise RuntimeError(
				"No aes_key specified in asab:storage configuration. "
				"If you want to use encryption, specify a non-empty aes_key."
			)

		if not isinstance(encrypted, bytes):
			raise TypeError("Only values of type 'bytes' can be decrypted")

		# Strip the prefix
		if not encrypted.startswith(ENCRYPTED_PREFIX):
			raise ValueError("Encrypted data must start with {!r} prefix".format(ENCRYPTED_PREFIX))
		encrypted = encrypted[len(ENCRYPTED_PREFIX):]

		# Separate the initialization vector
		iv, encrypted = encrypted[:block_size], encrypted[block_size:]

		algorithm = cryptography.hazmat.primitives.ciphers.algorithms.AES(self._AESKey)
		mode = cryptography.hazmat.primitives.ciphers.modes.CBC(iv)
		cipher = cryptography.hazmat.primitives.ciphers.Cipher(algorithm, mode)
		decryptor = cipher.decryptor()
		raw = decryptor.update(encrypted) + decryptor.finalize()

		# Strip padding
		raw = raw.rstrip(b"\x00")
		return raw


	def encryption_enabled(self) -> bool:
		"""
		Check if AESKey is not empty.

		Returns:
			True if AESKey is not empty.
		"""
		return self._AESKey is not None
