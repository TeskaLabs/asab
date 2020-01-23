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

Following additional rules apply for imports:

1. Use relative imports when you import locally from a package
2. Use absolute imports when you import from external package
3. Never use `from ... import ...` because it unnecessarily increases complexity for readers (unless you have very good reason for that). The only exception is `__init__.py` where it is used for importing symbols that you want to expose as a given module public API

### Documenting functions, methods and classes

Functions, methods and classes should be documented using quotation marks, see the example below

```
def publish(self, event_name, *args, **kwargs):
	""" Notify subscribers of an event with arguments. """

	callback_set = self.subscribers.get(event_name)
	...
```


## Publishing to pypi.org

1. Create a version tag (`git tag -a v19.10`)
1. Push a tag to GitHub (`git push origin v19.10`)
1. Make local build (`setup.py sdist bdist_wheel`)
1. Publish a package to pypi.org (`twine upload dist/*`)
