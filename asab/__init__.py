"""Asynchronous Server Application Boilerplate.

ASAB (Asynchronous Serverless Application Builder) is a lightweight Python framework for building
asynchronous and serverless applications. It provides a simple yet powerful set of tools and
conventions for developing scalable and efficient applications.

For detailed documentation and examples, please refer to the ASAB documentation at:
	- GitHub Repository: https://github.com/TeskaLabs/asab
	- Documentation: https://asab.readthedocs.io
"""

import logging

from .abc.module import Module
from .abc.service import Service
from .abc.singleton import Singleton
from .application import Application
from .config import Config, ConfigObject, Configurable
from .log import LOG_NOTICE
from .pdict import PersistentDict
from .pubsub import subscribe, PubSub, Subscriber
from .socket import StreamSocketServerService
from .timer import Timer

from .__version__ import __version__, __build__

# This logger is used to indicate use of the obsolete function
# Example:
#    asab.LogObsolete.warning("Use of the obsolete function", struct_data={'eol':'2022-31-12'})
# See https://github.com/TeskaLabs/asab/issues/240
LogObsolete = logging.getLogger('OBSOLETE')

__all__ = (
	'Module',
	'Service',
	'Singleton',
	'Application',
	'Config',
	'Configurable',
	'ConfigObject',
	'LOG_NOTICE',
	'PersistentDict',
	'subscribe',
	'PubSub',
	'Subscriber',
	'StreamSocketServerService',
	'Timer',
	'__version__',
	'__build__',
)
