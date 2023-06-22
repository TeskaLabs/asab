Encryption and decryption
-------------------------

Data stored in the database can be encrypted using an algorithm that
adheres to the Advanced Encryption Standard (AES).

### AES Key settings

In order to use encryption, first make sure you have the [cryptography
package](https://pypi.org/project/cryptography/) installed. Then specify
the AES Key in the config file.

``` {.ini}
[asab:storage]
aes_key=random_key_string
```

xxx {.note}
xxx {.title}
Note
xxx

The AES Key is used as both an encryption and decryption key. It is
recommended to keep it in [a separate configuration
file](https://asab.readthedocs.io/en/latest/asab/config.html#including-other-configuration-files)
that is not exposed anywhere publicly.

The actual binary AES Key is obtained from the [aes_key]{.title-ref}
specified in the config file by encoding and hashing it using the
standard [hashlib](https://docs.python.org/3/library/hashlib.html)
algorithms, so do not worry about the length and type of the key.
xxx

### Encrypting data

The `Upsertor.set()`{.interpreted-text role="func"} method has an
optional boolean parameter [encrypt]{.title-ref} for encrypting the data
before they are stored. Only values of the type `bytes` can be
encrypted. If you want to encrypt other values, encode them first.

``` {.python}
message = "This is a super secret message!"
number = 2023
message_binary = message.encode("ascii")
number_binary = number.encode("ascii")

u.set("message", message_binary, encrypt=True)
u.set("number", number_binary, encrypt=True)
object_id = await u.execute()
```

### Decrypting data

The `StorageService.get()`{.interpreted-text role="func"} coroutine
method has an optional parameter [decrypt]{.title-ref} which takes an
`iterable` object (i.e. a list, tuple, set, ...) with the names of keys
whose values are to be decrypted.

``` {.python}
data = await storage.get(
    collection="test-collection", 
    obj_id=object_id, 
    decrypt=["message", "number"]
    )
```

If some of the keys to be decrypted are missing in the required
document, the method will ignore them and continue.

xxx {.note}
xxx {.title}
Note
xxx

Data that has been encrypted can be identified by the prefix
"$aes-cbc$" and are stored in a binary format.
xxx

### Under the hood

For encrypting data, we use the certified symmetric AES-CBC algorithm.
In fact, the abstract base class `StorageServiceABC`{.interpreted-text
role="class"} provides two methods `aes_encrypt()`{.interpreted-text
role="func"} and `aes_decrypt()`{.interpreted-text role="func"} that are
called automatically in `Upsertor.set()`{.interpreted-text role="func"}
and `StorageService.get()`{.interpreted-text role="func"} methods when
the parameter [encrypt]{.title-ref} or [decrypt]{.title-ref} is
specified.

AES-CBC is a mode of operation for the Advanced Encryption Standard
(AES) algorithm that provides confidentiality and integrity for data. In
AES-CBC, the plaintext is divided into blocks of fixed size (usually 128
bits), and each block is encrypted using the AES algorithm with a secret
key.

CBC stands for "Cipher Block Chaining" and it is a technique that adds
an extra step to the encryption process to ensure that each ciphertext
block depends on the previous one. This means that any modification to
the ciphertext will produce a completely different plaintext after
decryption.

The algorithm is a symmetric cipher, which is suitable for encrypting
large amounts of data. It requires much less computation power than
asymmetric ciphers and is much more useful for bulk encrypting large
amounts of data.
