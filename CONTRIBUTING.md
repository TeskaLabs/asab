# Contributing to ASAB


This document outlines some of the conventions for contributing to ASAB code.


## Coding conventions

ASAB is a Python project.


### Imports

Imports shall be writen one-per-line style as per the example below

```
import os
import sys
import logging
...
```


### Documenting functions, methods and classes

Functions, methods and classes should be documented using quotation marks, see the example below

```
def publish(self, event_name, *args, **kwargs):
	""" Notify subscribers of an event with arguments. """

	callback_set = self.subscribers.get(event_name)
	...
```


## Publishing to pypi.org

1. Adjust `asab.__init__.py` `__version__` string
1. Create a version tag
2. Push a tag to GitHub
3. Release a package to pypi.org:

```
python3.7 setup.py sdist
twine upload --repository-url https://upload.pypi.org/legacy/ dist/asab-18.12b1.tar.gz
```
