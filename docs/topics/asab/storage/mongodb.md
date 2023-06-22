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
