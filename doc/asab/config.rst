Configuration
=============

The configuration is provided as ``asab.Config`` object which is a singleton. It means that you can access ``asab.Config`` from any place of your code, without need of explicit initialisation.

The configuration is automatically loaded from a configuration file during initialiation time of ``asab.Application``.

The default name of a configuration file is ``./etc/[name-of-executable].conf`` but it could be specified by ``-c`` command-line argument, by ``ASAB_CONFIG`` environment variable or by config ``[general] config_file`` default value.


Based on ConfigParser
---------------------

The  ``asab.Config`` is inherited from Python Standard Library ``configparser.ConfigParser`` class. 


Including configuration files
-----------------------------

TODO: Document includes


Configuration default values
----------------------------

TODO: Document defaults


Environment variables in configration
-------------------------------------

TODO: Document environment variables


asab.Config object
------------------

.. py:class:: asab.Config(configparser.ConfigParser)

	``asab.Config`` provides a configuration to ASAB application.

	.. py:method:: add_defaults(dictionary)

		Add default values to a configuration.


		.. code:: python

			asab.Config.add_defaults(
			    {
			        'section2_name': {
			            'key1': 'value',
			            'key2': 'another value'
			        }
			    }
			)

