Creating a microservice with REST API
=====================================

In the [previous tutorial](./02_web_server.md), you have learned how to create a web server.

With this tutorial, you will create a basic ASAB microservice that
provides a REST HTTP API. This microservice will implement Create, Read,
Update and Delete functionality, in another words CRUD. MongoDB will be
used as the database.

Prerequisites
-------------

1.  Python version 3.6 or later
2.  Asynchronous Server App Boilerplate (ASAB) version 20.3 or later
3.  MongoDB instance
4.  Postman

xxx {.note}
xxx {.title}
Note
xxx

We will use Docker to run MongoDB. Docker installation is not covered in
this tutorial, but there are scores of good ones online should you run
into any trouble. If you\'re not familiar with Docker yet, it is a great
opportunity to start (<https://www.docker.com/get-started/>).

Otherwise, you can install MongoDB following one of these tutorials:
<https://www.mongodb.com/docs/manual/installation/>
xxx

Components
----------

The microservice consists of several modules (aka Python files). These
modules are as follows (and also indicate the file structure) and will
be discussed in more detail in the respective sections below, going from
top to bottom:

``` {.}
.
└── myrestapi.py
─── myrestapi
    └── __init__.py
    ─── app.py
    ─── tutorial
        └── handler.py
        └── service.py
```

MongoDB
-------

To make things simple, let\'s use a Docker image.

Pull this image: <https://hub.docker.com/_/mongo>

You can simply use the command below to run it. If you choose to run the
instance without a password, don\'t forget to adjust the related
**asab.Config** in [./myrestapi/app.py]{.title-ref}.

``` {.bash}
docker run -d -p 27017:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=user \
    -e MONGO_INITDB_ROOT_PASSWORD=secret \
    mongo
```

Postman
-------

We use Postman to test the webservice REST API.

You can download it here: <https://www.postman.com/downloads/>

The Postman is fairly straightforward to use. You can create your
collection of HTTP requests, save them, or automatically generate
documentation.

myrestapi.py
------------

This is where everything starts. Begin with the shebang line, which
tells the executing operating system **python** should execute this
program.

``` {.python}
#!/usr/bin/env python3
```

Imports follow. All you need here is the application. It is called
**TutorialApp**:

``` {.python}
from myrestapi import TutorialApp 
```

Next, instantiate an application class [TutorialApp]{.title-ref} in the
\_\_[main](#init__.py) of the application, and run it:

``` {.python}
if __name__ == '__main__':
    app = TutorialApp()   
    app.run()
```

app.py
------

[./myrestapi/app.py]{.title-ref}

Define the application class [TutorialApp]{.title-ref}.

Imports first:

``` {.python}
import asab
import asab.web
import asab.web.rest
import asab.storage
```

Add some default configuration:

``` {.python}
asab.Config.add_defaults(
{
    'asab:storage': {
        'type': 'mongodb',
        'mongodb_uri': 'mongodb://mongouser:mongopassword@mongoipaddress:27017',
        'mongodb_database': 'mongodatabase'
    },
})
```

xxx {.note}
xxx {.title}
Note
xxx

To make things more simple, Mongo credentials are stored here as a
default configuration. Usually, you provide your app with a
configuration file using [-c]{.title-ref} commandline option. Learn more
in section `configuration-ref`{.interpreted-text role="ref"}.
xxx

Next, describe the class, it inherits from the basic ASAB Application
class, but you need to expand it a little:

``` {.python}
class TutorialApp(asab.Application):

    def __init__(self):
        super().__init__()
        # Register modules
        self.add_module(asab.web.Module)
        self.add_module(asab.storage.Module)

        # Locate the web service
        self.WebService = self.get_service("asab.WebService")
        self.WebContainer = asab.web.WebContainer(
            self.WebService, "web"
        )
        self.WebContainer.WebApp.middlewares.append(
            asab.web.rest.JsonExceptionMiddleware
        )

        # Initialize services
        from .tutorial.handler import CRUDWebHandler
        from .tutorial.service import CRUDService
        self.CRUDService = CRUDService(self)
        self.CRUDWebHandler = CRUDWebHandler(
            self, self.CRUDService
        )
```

\_\_init\_\_.py
---------------

[./myrestapi/\_\_init\_\_.py]{.title-ref}

Init file is needed so myrestapi will work as a module. Just import the
TutorialApp.

``` {.python}
from .app import TutorialApp

__all__ = [
    "TutorialApp",
]
```

handler.py
----------

[./myrestapi/tutorial/handler.py]{.title-ref}

The handler is where HTTP Rest calls are handled and transformed into
the actual (internal) service calls. From another perspective, the
handler should contain only translation between REST calls and the
service interface. No actual \'business logic\' should be here. It is
strongly suggested to build these CRUD methods one by one and test them
straight away. If you haven\'t set up your database test instance yet,
now is the time to do it.

As usual, we start by importing modules:

``` {.python}
import asab
import asab.web.rest
```

Let\'s start with two methods - [create]{.title-ref} and
[read]{.title-ref} which allow us to write into database and check the
record.

``` {.python}
class CRUDWebHandler(object):
    def __init__(self, app, mongo_svc):
        self.CRUDService = mongo_svc
        web_app = app.WebContainer.WebApp
        web_app.router.add_put(
            '/crud-myrestapi/{collection}',
            self.create
        )
        web_app.router.add_get(
            '/crud-myrestapi/{collection}/{id}',
            self.read
        )


    @asab.web.rest.json_schema_handler({
        'type': 'object',
        'properties': {
            '_id': {'type': 'string'},
            'field1': {'type': 'string'},
            'field2': {'type': 'number'},
            'field3': {'type': 'number'}
        }})
    async def create(self, request, *, json_data):
        collection = request.match_info['collection']

        result = await self.CRUDService.create(
            collection, json_data
        )
        if result:
            return asab.web.rest.json_response(
                request, {"result": "OK"}
            )
        else:
            asab.web.rest.json_response(
                request, {"result": "FAILED"}
            )


    async def read(self, request):
        collection = request.match_info['collection']
        key = request.match_info['id']
        response = await self.CRUDService.read(
            collection, key
        )
        return asab.web.rest.json_response(
            request, response
        )
```

The handler only accepts the incoming requests and returns appropriate
responses. All of the \"logic\", be it the specifics of the database
connection, additional validations and other operations take place in
the CRUDService.

POST and PUT requests typically come with data in their body. Providing
your [WebContainer]{.title-ref} with
[JsonExceptionMiddleware]{.title-ref} enables you to validate a JSON
input using [\@asab.web.rest.json\_schema\_handler]{.title-ref}
decorator and JSON schema (<https://json-schema.org/>).

xxx {.note}
xxx {.title}
Note
xxx

ASAB WebServer is built on top of the aiohttp library. For further
details please visit <https://docs.aiohttp.org/en/stable/index.html>.
xxx

service.py
----------

[./myrestapi/tutorial/service.py]{.title-ref}

As mentioned above, this is where the inner workings of the microservice
request processing are. Let\'s start as usual, by importing the desired
modules:

``` {.python}
import asab
import asab.storage.exceptions
```

We want to start logging in here:

``` {.python}
import logging
#

L = logging.getLogger(__name__)

#
```

Now define the CRUDService class which inherits from the
[asab.Service]{.title-ref} class.

xxx {.note}
xxx {.title}
Note
xxx

[asab.Service]{.title-ref} is a lightweight yet powerful abstract class
providing your object with 3 functionalities:

-   Name of the [asab.Service]{.title-ref} is registered in the app and
    can be called from the [app]{.title-ref} object anywhere in your
    code.
-   [asab.Service]{.title-ref} class implements
    [initialize()]{.title-ref} and [finalize()]{.title-ref} coroutines
    which help you to handle asynchronous operations in init and exit
    time of your application.
-   [asab.Service]{.title-ref} registers application object as
    [self.App]{.title-ref} for you.
xxx

``` {.python}
class CRUDService(asab.Service):

    def __init__(self, app, service_name='crud.CRUDService'):
        super().__init__(app, service_name)
        self.MongoDBStorageService = app.get_service(
            "asab.StorageService"
        )

    async def create(self, collection, json_data):
        obj_id = json_data.pop("_id")

        cre = self.MongoDBStorageService.upsertor(
            collection, obj_id
        )

        for key, value in zip(
            json_data.keys(), json_data.values()
        ):
            cre.set(key, value)

        try:
            await cre.execute()
            return "OK"
        except asab.storage.exceptions.DuplicateError:
            L.warning(
                "Document you are trying to create already exists."
            )
            return None

    async def read(self, collection, obj_id):
        response = await self.MongoDBStorageService.get(
            collection, obj_id
        )
        return response
```

[asab.StorageService]{.title-ref} initialized in [app.py]{.title-ref} as
part of the [asab.storage.Module]{.title-ref} enables connection to
MongoDB. Further on, two methods provide the handler with the desired
functionalities.

Now test it!
------------

The application is implicitly running on an **8080** port. Open the
Postman and set a new request.

Try the PUT method:

``` {.}
127.0.0.1:8080/crud-myrestapi/movie
```

Insert into the request body:

``` {.}
{
"_id": "1",
"field1": "something new",
"field2": 5555,
"field3": 44424
}
```

When there\'s a record in your database, try to read it! For example
with this GET request:

``` {.}
127.0.0.1:8080/crud-myrestapi/movie/1
```

Is your response with a 200 status code? Does it return desired data?

xxx {.note}
xxx {.title}
Note
xxx

**TROUBLESHOOTING**

**ERROR**

``` {.}
ModuleNotFoundError: No module named 'pymongo.mongo_replica_set_client'
```

Try:

``` {.}
pip install motor
```

**ERROR**

``` {.}
OSError: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8080): address already in use
```

Try to kill process listening on 8080 or add \[web\] section into
configuration:

``` {.}
asab.Config.add_defaults(
{
    'asab:storage': {
        'type': 'mongodb',
        'mongodb_uri': 'mongodb://mongouser:mongopassword@mongoipaddress:27017',
        'mongodb_database': 'mongodatabase'
    },
    'web': {
        'listen': '0.0.0.0 8081'
    }
})
```

**ERROR**

No error at all, no response either.

Try to check the Mongo database credentials. Do your credentials in the
configuration in [app.py]{.title-ref} fit the ones you entered when
running the Mongo Docker image?
xxx

Up and running! Congratulation on your first ASAB microservice!

Oh, wait\...

**C**, **R**\... What about **Update** and **Delete** you ask?

You already know everything to add the next functionality! Accept the
challenge and try it yourself! Or check out the code below.

Update and Delete
-----------------

**handler.py**

[./myrestapi/tutorial/handler.py]{.title-ref}

``` {.python}
import asab
import asab.web.rest


class CRUDWebHandler(object):
    def __init__(self, app, mongo_svc):
        self.CRUDService = mongo_svc
        web_app = app.WebContainer.WebApp
        web_app.router.add_put(
            '/crud-myrestapi/{collection}',
            self.create
        )
        web_app.router.add_get(
            '/crud-myrestapi/{collection}/{id}',
            self.read
        )
        web_app.router.add_put(
            '/crud-myrestapi/{collection}/{id}',
            self.update
        )
        web_app.router.add_delete(
            '/crud-myrestapi/{collection}/{id}',
            self.delete
        )


    @asab.web.rest.json_schema_handler({
        'type': 'object',
        'properties': {
            '_id': {'type': 'string'},
            'field1': {'type': 'string'},
            'field2': {'type': 'number'},
            'field3': {'type': 'number'}
        }})
    async def create(self, request, *, json_data):
        collection = request.match_info['collection']

        result = await self.CRUDService.create(
            collection, json_data
        )
        if result:
            return asab.web.rest.json_response(
                request, {"result": "OK"}
            )
        else:
            asab.web.rest.json_response(
                request, {"result": "FAILED"}
            )


    async def read(self, request):
        collection = request.match_info['collection']
        key = request.match_info['id']
        response = await self.CRUDService.read(
            collection, key
        )
        return asab.web.rest.json_response(
            request, response
        )


    @asab.web.rest.json_schema_handler({
        'type': 'object',
        'properties': {
            '_id': {'type': 'string'},
            'field1': {'type': 'string'},
            'field2': {'type': 'number'},
            'field3': {'type': 'number'}
        }})
    async def update(self, request, *, json_data):
        collection = request.match_info['collection']
        obj_id = request.match_info["id"]

        result = await self.CRUDService.update(
            collection, obj_id, json_data
        )
        if result:
            return asab.web.rest.json_response(
                request, {"result": "OK"}
            )
        else:
            asab.web.rest.json_response(
                request, {"result": "FAILED"}
            )


    async def delete(self, request):
        collection = request.match_info['collection']
        obj_id = request.match_info["id"]
        result = await self.CRUDService.delete(
            collection, obj_id
        )

        if result:
            return asab.web.rest.json_response(
                request, {"result": "OK"}
            )
        else:
            asab.web.rest.json_response(
                request, {"result": "FAILED"}
            )
```

**service.py**

[./myrestapi/tutorial/service.py]{.title-ref}

``` {.python}
import asab
import asab.storage.exceptions

import logging
#

L = logging.getLogger(__name__)

#


class CRUDService(asab.Service):

    def __init__(self, app, service_name='crud.CRUDService'):
        super().__init__(app, service_name)
        self.MongoDBStorageService = app.get_service(
            "asab.StorageService"
        )

    async def create(self, collection, json_data):
        obj_id = json_data.pop("_id")

        cre = self.MongoDBStorageService.upsertor(
            collection, obj_id
        )

        for key, value in zip(
            json_data.keys(), json_data.values()
        ):
            cre.set(key, value)

        try:
            await cre.execute()
            return "OK"
        except asab.storage.exceptions.DuplicateError:
            L.warning(
                "Document you are trying to create already exists."
            )
            return None


    async def read(self, collection, obj_id):
        response = await self.MongoDBStorageService.get(
            collection, obj_id
        )
        return response


    async def update(self, collection, obj_id, document):
        original = await self.read(
            collection, obj_id
        )

        cre = self.MongoDBStorageService.upsertor(
            collection, original["_id"], original["_v"]
        )

        for key, value in zip(
            document.keys(), document.values()
        ):
            cre.set(key, value)

        try:
            await cre.execute()
            return "OK"

        except KeyError:
            return None


    async def delete(self, collection, obj_id):
        try:
            await self.MongoDBStorageService.delete(
                collection, obj_id
            )
            return True
        except KeyError:
            return False
```
