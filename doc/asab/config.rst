Configuration
=============

.. py:currentmodule:: asab

.. py:data:: Config

The configuration is provided by :py:obj:`Config` object which is a singleton. It means that you can access :py:obj:`Config` from any place of your code, without need of explicit initialisation.

.. code:: python

	import asab
	
	# Initialize application object and hence the configuration
	app = asab.Application()

	# Access configuration values anywhere
	my_conf_value = asab.Config['section_name']['key1']


Based on ConfigParser
---------------------

The  :py:obj:`Config` is inherited from Python Standard Library :py:class:`configparser.ConfigParser` class. which implements a basic configuration language which provides a structure similar to what’s found in Microsoft Windows INI files. 

.. py:currentmodule:: asab.config

.. py:class:: ConfigParser

Example of the configuration file:

.. code:: ini

	[bitbucket.org]
	User = hg

	[topsecret.server.com]
	Port = 50022
	ForwardX11 = no


And this is how you access configuration values:

.. code:: python

	>>> asab.Config['topsecret.server.com']['ForwardX11']
	'no'


.. py:currentmodule:: asab


Automatic load of configuration
-------------------------------

If a configuration file name is specified, the configuration is automatically loaded from a configuration file during initialiation time of :py:class:`Application`.
The configuration file name can be specified by one of ``-c`` command-line argument (1), ``ASAB_CONFIG`` environment variable (2) or config ``[general] config_file`` default value (3).

.. code:: shell

	./sample_app.py -c ./etc/sample.conf



Including other configuration files
-----------------------------------

You can specify one or more additional configuration files that are loaded and merged from an main configuration file.
It is done by ``[general] include`` configuration value. Multiple paths are separated by ``os.pathsep`` (``:`` on Unix).
The path can be specified as a glob (e.g. use of ``*`` and ``?`` wildcard characters), it will be expanded by ``glob`` module from Python Standard Library.
Included configuration files may not exists, this situation is silently ignored.

.. code:: ini

	[general]
	include=./etc/site.conf:./etc/site.d/*.conf



Configuration default values
----------------------------

.. py:method:: Config.add_defaults(dictionary)

This is how you can extend configuration default values:

.. code:: python

	asab.Config.add_defaults(
	    {
	        'section_name': {
	            'key1': 'value',
	            'key2': 'another value'
	        },
	        'other_section': {
	            'key3': 'value',
	        },
	    }
	)



Environment variables in configration
-------------------------------------

Environment variables found in values are automatically expanded.

.. code:: ini

	[section_name]
	persistent_dir=${HOME}/.myapp/

.. code:: python

	>>> asab.Config['section_name']['persistent_dir']
	'/home/user/.myapp/'



