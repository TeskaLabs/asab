
Manipulation with databases
---------------------------

### Upsertor

Upsertor is an object that works like a pointer to the specified
database and optionally to object id. It is used for inserting new
objects, updating existing objects and deleting them.

``` python
u = storage.upsertor("test-collection")
```

The `StorageService.upsertor()` method
creates an upsertor object associated with the specified collection. It
takes [collection]{.title-ref} as an argument and can have two
parameters [obj_id]{.title-ref} and [version]{.title-ref}, which are
used for getting an existing object by its ID and version.

### Inserting an object

For inserting an object to the collection, use the `Upsertor.set()` method.

``` python
u.set("key", "value")
```

To execute these procedures, simply run the `Upsertor.execute()` coroutine method, which commits the upsertor data to the storage and returns the ID of the object. Since it is a coroutine, it must be awaited.

``` python
object_id = await u.execute()
```

The `Upsertor.execute()` method has optional parameters `custom_data` and `event_type`, which are used for webhook requests.

``` python
object_id = await u.execute(
    custom_data= {"foo": "bar"},
    event_type="object_created"
    )
```

### Getting a single object

For getting a single object, use
`StorageService.get()`coroutine method
that takes two arguments `collection` and
`obj_id` and finds an object by its ID in collection.

``` python
obj = await storage.get(collection="test-collection", obj_id=object_id)
print(obj)
```

When the requested object is not found in the collection, the method
raises `KeyError`. Remember to handle this exception properly when using
databases in your services and prevent them from crashing!

!!! quote "Made with ❤️ by TeskaLabs"

!!! note
```
    MongoDB storage service in addition provides a coroutine method
    `get_by()`{.interpreted-text role="func"} which is used for accessing an
    object by finding its key-value pair.

    ``` python
    obj = await storage.get_by(database="test-collection", key="key", value="value")
    ```
```

### Updating an object

For updating an object, first obtain the upsertor specifying its
[obj_id]{.title-ref} and [version]{.title-ref}.

``` python
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
(Upsertor.set)(reference/storage/upsertor/#asab.storage.upsertor.UpsertorABC.set) coroutine.

``` python
u.set("key", "new_value")
object_id = await u.execute()
```

### Deleting an object

For deleting an object from database, use the
`StorageService.delete()`{.interpreted-text role="func"} coroutine
method which takes arguments [collection]{.title-ref} and
[obj_id]{.title-ref}, deletes the object and returns its ID.

``` python
deleted_id = await u.delete("test-collection", object_id)
```
