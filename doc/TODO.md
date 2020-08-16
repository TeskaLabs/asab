Undocumented items:
	
	- Compatibility with pypy
	- asab.web
		- asab.web websocket pubsub
		- sessions
	- Configuration default values (aka ConfigParser._default_values)
	- asab.storage
	- custom arg parser
	- config object
		- ConfigDefaults can contain only basic types (int, string, boolean, float)
	- asab in Docker (how to build ASAB docker image and write how to deploy apps into a container derived from that image)
	- Metrics service
	- config var_dir + app method ensure_var_dir() that actually creates var directory if needed
	- Proactor service
	- MOM topic subscriptions
	- LogMan.io service
	- Web Rest object introspection (.get_rest() JSON serializer)
	- app.LaunchTime (and app.BaseTime)
	- ASAB networking (move StreamSocket class there)
	- asab.web.authn (basic auth, oauth, public key)
	- ASAB alerts

Enhancements:

    - Configuration priority:
    	High: Configuration Overrides in the code
    	Site config files (includes)
    	Main configuration file
    	Low: ConfigDefaults in the code

