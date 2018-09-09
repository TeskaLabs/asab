Undocumented items:
	
	- Compatibility with pypy
	- asab.web
		- asab.web websocket pubsub
		- sessions
	- Configuration default values (aka ConfigParser._default_values)
	- asab.storage
	- custom arg parser
	- config object
	- asab in Docker (how to build ASAB docker image and write how to deploy apps into a container derived from that image)
	- Metrics service
	- config var_dir + app method ensure_var_dir() that actually creates var directory if needed

Enhancements:

    - Configuration priority:
    	High: Configuration Overrides in the code
    	Site config files (includes)
    	Main configuration file
    	Low: ConfigDefaults in the code

