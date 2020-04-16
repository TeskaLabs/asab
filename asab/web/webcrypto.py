import base64
import secrets

import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
import cryptography.hazmat.backends

'''
This module provides AES GCM based payload protection.

Flow:

1. aes_gcm_generate_key() to get JWT AES 256 GCM key
2. Deliver the key to a Javascript app, also store AES key on the server
3. Import the key in the Javascript

	window.crypto.subtle.importKey(
		"jwk",
		jwt_aes_key,
		{ name: "AES-GCM" },
		false,
		["encrypt", "decrypt"]
	)
	.then(function(key){
		... use_the_key_here ...
	})
	.catch(function(err){
		console.error(err);
	});

4. Encrypt the payload in Javascript

	const iv = window.crypto.getRandomValues(new Uint8Array(12));
	window.crypto.subtle.encrypt(
		{
			name: "AES-GCM",
			iv: iv,
			// Optionally provide additionalData: ,
			tagLength: 128,
		},
		key, //from importKey above
		plaintext
	)
	.then(function(ciphertext){

		axios.post('/api/...',
			concatUint8ArrayAndArrayBuffer(iv, ciphertext),
		)
	}

5. Submit the payload to the server, don't send AES key with it!

5. Decrypt the payload on the server side
	plaintext = aes_gcm_decrypt(key = key_from_generate, ciphertext)

'''


def aes_gcm_decrypt(key: bytes, ciphertext: bytes, associated_data: bytes = None) -> bytes:
	'''
	Decrypt the ciphertext that is encrypted by AES GCM.
	'''

	iv = ciphertext[:12]
	message = ciphertext[12:-16]
	tag = ciphertext[-16:]

	# Construct a Cipher object, with the key, iv, and additionally the
	# GCM tag used for authenticating the message.
	decryptor = cryptography.hazmat.primitives.ciphers.Cipher(
		cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
		cryptography.hazmat.primitives.ciphers.modes.GCM(iv, tag),
		backend=cryptography.hazmat.backends.default_backend()
	).decryptor()

	# We put associated_data back in or the tag will fail to verify
	# when we finalize the decryptor.
	if associated_data is not None:
		decryptor.authenticate_additional_data(associated_data)

	# Decryption gets us the authenticated plaintext.
	# If the tag does not match an InvalidTag exception will be raised.
	return decryptor.update(message) + decryptor.finalize()


def aes_gcm_generate_key(key: bytes = None) -> dict:
	'''
	Generate JWT AES 256 GCM key.
	'''

	if key is None:
		key = secrets.token_bytes(256 // 8)

	# JWT key
	return {
		"kty": "oct",
		"k": base64.urlsafe_b64encode(key).decode('ascii').rstrip('='),
		"alg": "A256GCM",
		"ext": True,
	}
