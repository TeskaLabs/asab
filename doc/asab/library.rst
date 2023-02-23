.. _library-ref:

Library
=======

.. py:currentmodule:: asab.library

The ASAB Library (`asab.library`) is a concept of the shared data content across microservices.
The `asab.library` is read-only interface for listing and reading this content.
The library can also notify the ASAB microservice about changes in underlaying library, eg. for automated update/reload.

The library content is organized in simplified filesystem manner, with directories and files.

There is a companion microservice `asab-library` that can be used for management and editation of the content.
The `asab.library` can however operate without `asab-library`.


Path rules
----------

 * The path must start with `/`, including the root path (`/`).
 * The directory path must end with `/`.
 * The file path must end with extension (eg. `.json`).


Providers
---------

The library can be configured to work with following "backends" (aka providers):

* Filesystem
* Apache Zookeeper
* Microsoft Azure Storage
* git repository

Layers
------

The library content can be organized into unlimmited number of layers.
Each layer is represented by a `provider` with a specific configuration.


