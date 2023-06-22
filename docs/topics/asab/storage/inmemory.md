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