Creating a microservice with REST API
=====================================

In the [previous tutorial](./02_web_server.md), you have learned how to create a web server.

With this tutorial, you will create a basic ASAB microservice that
provides a REST HTTP API. This microservice will implement **CREATE**, **READ**, **UPDATE** and **DELETE** functionality, in another words: **CRUD**. 
We will also use [MongoDB](https://www.mongodb.com/) as a database running on [Docker](https://docs.docker.com/), and . In case you are not familiar with these technologies, take the opportunity to learn their basics concepts, as they are alpha-omega of the backend programming.

Set up the project with Docker and MongoDB
------------------------------------------

Here are the steps:

1. **Install Docker** if you don't have it already. Go to [the official website](https://docs.docker.com/get-docker/), choose your operating system and follow the guide.
    
    !!! tip
        Take it as a recommendation from the experience of the authors of this tutorial that in most cases there is no need to install a Docker desktop, but the Docker engine will suffice. In some cases, installing Docker desktop may cause problems when interacting with Docker in the terminal.
    
    You can always check if you have Docker installed successfully:
    ``` bash
    docker --version
    ```

2. **Pull the MongoDB image** from Docker Hub.
``` bash
docker pull mongo
```
Start the container:
``` bash
docker run -d -p 27017:27017 \
    -e MONGO_INITDB_ROOT_USERNAME=user \
    -e MONGO_INITDB_ROOT_PASSWORD=secret \
    mongo
```

3. **Install Postman** in case you do not have it. We will use it to test the webservice REST API.
You can download it from [the official website](https://www.postman.com/downloads/).
The Postman is fairly straightforward to use. You can create your
collection of HTTP requests, save them, or automatically generate
documentation.

4. **Prepare the structure of the project.** Every asab microservice consists of several Python modules.
Create the following file structure in your repository:

    ```
    .
    └── my_rest_api.py
    ─── my_rest_api
        └── __init__.py
        ─── app.py
        ─── tutorial
            └── handler.py
            └── service.py
    ─── conf
        └── config.ini
    ```


Build a microservice
--------------------

With the prepared modules, we move on to actual coding. Here is the code for every module with explanations.


``` python title="my_rest_api.py"
#!/usr/bin/env python3  # (1)!
from my_rest_api import TutorialApp  # (2)!

if __name__ == '__main__':  # (3)!
    app = TutorialApp()   
    app.run()
```

1. This is the executable file used to run the application via `python my_rest_api.py` command.
2. The asab application will be stored in `my_rest_api` module.
3. As always, we start the application by creating it's singleton and executing the  `run()` method.

```python title="my_rest_api/app.py"

import asab # (1)!
import asab.web
import asab.web.rest
import asab.storage # (2)!

class TutorialApp(asab.Application):

    def __init__(self):
        super().__init__() # (3)!

        # Register modules
        self.add_module(asab.web.Module) # (4)!
        self.add_module(asab.storage.Module)

        # Locate the web service  
        self.WebService = self.get_service("asab.WebService") # (5)!
        self.WebContainer = asab.web.WebContainer(
            self.WebService, "web" # (6)!
        )
        self.WebContainer.WebApp.middlewares.append(
            asab.web.rest.JsonExceptionMiddleware # (7)!
        )

        # Initialize services # (8)!
        from .tutorial.handler import CRUDWebHandler
        from .tutorial.service import CRUDService
        self.CRUDService = CRUDService(self)
        self.CRUDWebHandler = CRUDWebHandler(
            self, self.CRUDService
        )
```

1. As always, let's start with importing the `asab` modules.

2. This module is a built-in asab service which is used for manipulation with databases.

3. Remember, if you override a `__init__()` method, don't forget to add this super-initialization line of code.

4. `asab` modules are registered with the `add_module()` method on the `asab.Application` object.

5. To access the web service, use the `get_service()` method. It is common to have all the services stored as attributes on the `asab.Application` object.

6. TODO
7. TODO

8. `asab` microservices consist of two parts: **services** and **handlers**. 
When HTTP request is sent to the web server, **handler** will identify its type and calls the corresponding **service**. The service performs some operations and returns some data back to the handler, which sends it back to the client.


Continue with the init file, so that the directory `my_rest_api` will work as a module.

``` python title="my_rest_api/__init__.py"
from .app import TutorialApp

__all__ = [
    "TutorialApp", # (1)!
]
```

1. The list of strings that define what variables have to be imported to another file. If you don't know, what is going on, [this explanation](https://www.geeksforgeeks.org/python-__all__/) could help. In this case, we only want to import `TutorialApp` class.

Create a handler
----------------

The handler is where HTTP Rest calls are handled and transformed into
the actual (internal) service calls. From another perspective, the
handler should contain only translation between REST calls and the
service interface. No actual 'business logic' should be here. It is
strongly suggested to build these CRUD methods one by one and test them
straight away.

``` python title="my_rest_api/tutorial/handler.py" linenums="1"

import asab
import asab.web.rest


class CRUDWebHandler(object):
    def __init__(self, app, mongo_svc):
        self.CRUDService = mongo_svc # (1)!
        web_app = app.WebContainer.WebApp

        # Handle PUT and GET requests
        web_app.router.add_put(
            '/crud-myrestapi/{collection}', # (2)!
            self.create
        )
        web_app.router.add_get(
            '/crud-myrestapi/{collection}/{id}',
            self.read
        )

        self.JSONSchema = { # (3)!
        'type': 'object',
            'properties': {
                '_id': {'type': 'string'},
                'name': {'type': 'string'},
                'age': {'type': 'number'},
                'job': {'type': 'string'}
            }
        }


    @asab.web.rest.json_schema_handler(self.JSONSchema) # (4)!
    async def create(self, request, *, json_data):
        collection = request.match_info['collection'] # (5)!

        result = await self.CRUDService.create(
            collection, json_data # (6)!
        )
        if result:  
            return asab.web.rest.json_response(
                request, {"result": "OK"} # (7)!
            )
        else:
            asab.web.rest.json_response(
                request, {"result": "FAILED"} # (8)!
            )

    async def read(self, request):
        collection = request.match_info['collection'] # (9)!
        key = request.match_info['id']

        response = await self.CRUDService.read(
            collection, key # (10)!
        )
        return asab.web.rest.json_response(
            request, response # (11)!
        )
```

1. This is a reference on the microservice. In this app, we will create a service which uses the MongoDB Storage.

2. Methods `add_put`, `add_get` take arguments `path`, which specifies the endpoint, and `handler`, which is a coroutine that is called after the request is received from the client. In fact, these methods are performed on [aiohttp web handler](https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.UrlDispatcher) and are special cases of the `add_route` method. In this case, the the path is `/crud-myrestapi/{collection}`, where collection is a variable name.

3. In order to prevent storing arbitrary data, we define a [JSON schema](https://json-schema.org/). Now if the request data do not satisfy the format, they cannot be posted to the database.

4. The JSON schema handler is used as a decorator and validates JSON documents by [JSON schema](https://json-schema.org/). It takes either a dictionary with the schema itself (as in this example), or a string with the path for the JSON file to look at.

5. This method is used for matching data from the URI. They must be listed in the brackets such as `{collection}` on line 12.

6. After the request is sent and the handler calls the `create` method, it calls a method with the same name on the service, expecting from it to perform some logic ("save `json_data` into `database`") and then return some data back.

7. Now if the service has returned some data back, the handler will send a positive response to the client...

8. ...or negative if the service didn't return anything.

9. Once again, obtain the data from the path.

10. After the `GET` request is sent, the handler calls the service to perform a method `read()`, expecting some data back.

11. Simply respond with the data found in the collection. If they do not exist, the response will be empty.

Let's start with two methods - `PUT` and `GET` which allow us to write into database and check the
record.

The handler only accepts the incoming requests and returns appropriate
responses. All of the "logic", be it the specifics of the database
connection, additional validations and other operations take place in
the CRUDService.


Create a service
----------------

``` python title="my_rest_api/tutorial/service.py"

import asab
import asab.storage.exceptions
import logging

L = logging.getLogger(__name__)


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

As mentioned above, this is where the inner workings of the microservice
request processing are. Let\'s start as usual, by importing the desired
modules:


Now define the CRUDService class which inherits from the
[asab.Service]{.title-ref} class.



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


[asab.StorageService]{.title-ref} initialized in [app.py]{.title-ref} as
part of the [asab.storage.Module]{.title-ref} enables connection to
MongoDB. Further on, two methods provide the handler with the desired
functionalities.

Create a configuration file
---------------------------


``` ini title="conf/config.ini"
[asab:storage]
type=mongodb
mongodb_uri='mongodb://mongouser:mongopassword@mongoipaddress:27017'
mongodb_database=mongodatabase
```


Testing the app
---------------

Now everything is prepared and we can test our application using Postman. Let's create a new collection named `celebrities` provided with some information.

1. Start the application
    ```
    python my_rest_api.py -c conf/config.ini
    ```

    The application is implicitly running on an [http://localhost:8080/](http://localhost:8080/) port. 

2. Open the Postman and set a new request.
   First try to add some data using `PUT` method to `localhost:8080/crud-myrestapi/celebrities` endpoint. Insert this JSON document into the request body:

    ``` json
    {
    "_id": "1",
    "name": "Johnny Depp",
    "age": 60,
    "job": "actor"
    }
    ```

    Hopefully you received a status 200! Let's add one more.

    ``` json
    {
    "_id": "2",
    "name": "Lady Gaga",
    "age": 37,
    "job": "singer"
    }
    ```

    Now let's test if we can request for some data. Use the `GET` method to `localhost:8080/crud-myrestapi/celebrities/1` endpoint, this time with no request body.

    Now, what is the response?

    !!! success

        Up and running! Congratulation on your first ASAB microservice!

    !!! failure
        If you see the following message:

        ``` bash
        ModuleNotFoundError: No module named 'pymongo.mongo_replica_set_client'
        ```

        that means there is a missing module, probably the [motor](https://motor.readthedocs.io/en/stable/) library, which provides an asynchronous driver for MongoDB. Try to fix it:

        ``` bash
        pip install motor
        ```

    !!! failure
        If you see the following message:

        ``` bash
        OSError: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8080): address already in use
        ```

        that means that the port is already used by some other application (have you exit the application from the previous tutorial?)
        To check, what is running on your port, try:

        ``` bash
        lsof | grep LISTEN
        ```

        or

        ``` bash
        lsof | grep localhost:8000
        ```

        If you something similar to the following output:

        ```
        python3   103203    user    7u     IPv4  1059624 0t0 TCP *:bbs (LISTEN)
        ```

        that means there is a running process using the port with ID 103203. 
        
        The first option is simply to stop the process:

        ```
        kill -9 103203
        ```
        (replace the ID with the corresponding ID from the previous output).

        The second option is to add these lines into the configuration file:

        ``` ini title="conf/config.ini"
        [web]
        listen=0.0.0.0:8081
        ```

        If you run the app again, it should be running on an [http://localhost:8081/](http://localhost:8081/) port. 

    !!! question

        You see no error at all, no response either.

        Try to check the Mongo database credentials. Do your credentials in the config file fit the ones you entered when running the Mongo Docker image?


Conclusion
----------

TODO TODO TODO


Exercise 0: Store JSON schema in the file
-----------------------------------------

In order to get used to the `asab.web.rest.json_schema_handler()` decorator, store the JSON schema in a separate file. Then pass its path as an argument to the decorator.


Exercise 1: Implement `POST` and `DELETE` methods
-------------------------------------------------

For updating and deleting data from the database, we should implement the methods `POST` and `DELETE`.

1. Implement `update()` and `delete()` methods to the `CRUDService` class. Use 


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
