Undocumented items:
	
	- Compatibility with pypy
	- -d -> daemonise (via python-daemon) + [general] 'pidfile', 'uid', 'gid', 'working_dir'
	- PersistentDict (there is example pdict.py)
	- asab.web
		- asab.web websocket pubsub
		- sessions
	- Configuration default values (aka ConfigParser._default_values)
	- `-s` command-line switch
	- logging to file
	- asab.storage
	- custom arg parser

Enhancements:

    - Configuration priority:
    	High: Configuration Overrides in the code
    	Site config files (includes)
    	Main configuration file
    	Low: ConfigDefaults in the code

