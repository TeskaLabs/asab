Storage
=======

The ASAB's Storage Service supports data storage in-memory or in
dedicated document databases, including
[MongoDB](https://www.mongodb.com/) and
[ElasticSearch](https://www.elastic.co/).

Configuration
-------------

First, specify the storage type in the configuration. The options for
the storage type are:

-   `inmemory`: Collects data directly in memory
-   `mongodb`: Collects data using MongoDB database. Depends on
    [pymongo](https://pymongo.readthedocs.io/en/stable/) and
    [motor](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html)
    libraries.
-   `elasticsearch`: Collects data using ElasticSearch database.
    Depends on [aiohttp](https://docs.aiohttp.org/en/latest/) library.

Storage Service provides a unified interface for accessing and
manipulating collections across multiple database technologies.

``` {.ini}
[asab:storage]
type=mongodb
```

For accessing the storage, simply add
[asab.storage.Module]{.title-ref}` when initializing and register the
service.

``` {.python}
class MyApplication(asab.Application):

    async def initialize(self):

        self.add_module(asab.storage.Module)

    async def main(self):
        storage = self.get_service("asab.StorageService")
```

Manipulation with databases
---------------------------

### Upsertor

Upsertor is an object that works like a pointer to the specified
database and optionally to object id. It is used for inserting new
objects, updating existing objects and deleting them.

``` {.python}
u = storage.upsertor("test-collection")
```

The `StorageService.upsertor()`{.interpreted-text role="func"} method
creates an upsertor object associated with the specified collection. It
takes [collection]{.title-ref} as an argument and can have two
parameters [obj_id]{.title-ref} and [version]{.title-ref}, which are
used for getting an existing object by its ID and version.

### Inserting an object

For inserting an object to the collection, use the
`Upsertor.set()`{.interpreted-text role="func"} method.

``` {.python}
u.set("key", "value")
```

To execute these procedures, simply run the
`Upsertor.execute()`{.interpreted-text role="func"} coroutine method,
which commits the upsertor data to the storage and returns the ID of the
object. Since it is a coroutine, it must be awaited.

``` {.python}
object_id = await u.execute()
```

The [Upsertor.execute()]{.title-ref} method has optional parameters
[custom_data]{.title-ref} and [event_type]{.title-ref}, which are used
for webhook requests.

``` {.python}
object_id = await u.execute(
    custom_data= {"foo": "bar"},
    event_type="object_created"
    )
```

### Getting a single object

For getting a single object, use
`StorageService.get()`{.interpreted-text role="func"} coroutine method
that takes two arguments [collection]{.title-ref} and
[obj_id]{.title-ref} and finds an object by its ID in collection.

``` {.python}
obj = await storage.get(collection="test-collection", obj_id=object_id)
print(obj)
```

When the requested object is not found in the collection, the method
raises `KeyError`. Remember to handle this exception properly when using
databases in your services and prevent them from crashing!

xxx {.note}
xxx {.title}
Note
xxx

MongoDB storage service in addition provides a coroutine method
`get_by()`{.interpreted-text role="func"} which is used for accessing an
object by finding its key-value pair.

``` {.python}
obj = await storage.get_by(database="test-collection", key="key", value="value")
```
xxx

### Updating an object

For updating an object, first obtain the upsertor specifying its
[obj_id]{.title-ref} and [version]{.title-ref}.

``` {.python}
u = storage.upsertor(
    collection="test-collection", 
    obj_id=object_id, 
    version=obj['_v']
)
```

We strongly recommend to read the version from the object such as above.
That creates a soft lock on the record. It means that if the object is
updated by other component in meanwhile, your upsertor will fail and you
should retry the whole operation. The new objects should have a version
set to 0, which is done by default.

After obtaining an upsertor, you can update the object via the
`Upsertor.set()`{.interpreted-text role="func"} coroutine.

``` {.python}
u.set("key", "new_value")
object_id = await u.execute()
```

### Deleting an object

For deleting an object from database, use the
`StorageService.delete()`{.interpreted-text role="func"} coroutine
method which takes arguments [collection]{.title-ref} and
[obj_id]{.title-ref}, deletes the object and returns its ID.

``` {.python}
deleted_id = await u.delete("test-collection", object_id)
```

Storing data in memory
----------------------

If the option [inmemory]{.title-ref} is set, ASAB will store data in its
own memory. In particular, [asab.StorageService]{.title-ref} is
initialized with an attribute [InMemoryCollections]{.title-ref} which is
a dictionary where all the collections are stored in.

xxx {.note}
xxx {.title}
Note
xxx

You can go through all the databases directly by accessing
[InMemoryCollections]{.title-ref} attribute, although we do not
recommend that.

``` {.python}
import pprint

storage = self.get_service("asab.StorageService")
pprint.pprint(storage.InMemoryCollections, indent=2)
```
xxx

Storing data in MongoDB
-----------------------

If the option [mongodb]{.title-ref} is set, ASAB will store data in
MongoDB database.

ASAB uses [motor library](https://pypi.org/project/motor/) which
provides non-blocking MongoDB driver for [asyncio]{.title-ref}.

You can specify the database name and URL for MongoDB in config file
(the following example is the default configuration):

``` {.ini}
[asab:storage]
type=mongodb
mongodb_uri=mongodb://localhost:27017
mongodb_database=asabdb
```

You can use all the methods from the abstract class. MongoDB Storage
class provides in addition two methods,
`StorageService.get_by()`{.interpreted-text role="func"} and
`StorageService.collection()`{.interpreted-text role="func"}.

The method `StorageService.get_by()`{.interpreted-text role="func"} is
used in the same way as `StorageService.get()`{.interpreted-text
role="func"} except that it takes the arguments [key]{.title-ref} and
[value]{.title-ref} instead of [obj_id]{.title-ref}.

``` {.python}
obj = await storage.get_by(database="test-collection", key="key", value="value")
```

The method `collection()`{.interpreted-text role="func"} is used for
accessing the database directly. It takes [collection]{.title-ref} as
the argument and returns
[motor.motor_asyncio.AsyncIOMotorCollection]{.title-ref} object, which
can be used for calling MongoDB directives.

``` {.python}
collection = await storage.collection("test-collection")
cursor = collection.find({})
while await cursor.fetch_next:
    data = cursor.next_object()
    pprint.pprint(data)
```

The full list of methods suitable for this object is described in the
[official
documentation](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html).

Storing data in ElasticSearch
-----------------------------

When using ElasticSearch, add configurations for URL, username and
password.

``` {.ini}
[asab:storage]
type=elasticsearch
elasticsearch_url=http://localhost:9200/
elasticsearch_username=JohnDoe
elasticsearch_password=lorem_ipsum_dolor?sit_amet!2023
```

You can also specify the [refreshing
parameter](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-refresh.html#docs-refresh)
and scroll timeout for [ElasticSearch Scroll
API](https://www.elastic.co/guide/en/elasticsearch//reference/current/scroll-api.html).

``` {.ini}
[asab:storage]
refresh=true
scroll_timeout=1m
```

ElasticSearch Storage provides in addition other methods for creating
index templates, mappings etc (see the Reference section).

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
