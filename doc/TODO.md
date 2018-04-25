Undocumented items:
	
	- Compatibility with pypy
	- -d -> daemonise (via python-daemon) + [general] 'pidfile', 'uid' and 'gid'
	- PersistentDict (there is example pdict.py)

Enhancements:

    - Configuration priority:
    	High: Configuration Overrides in the code
    	Site config files (includes)
    	Main configuration file
    	Low: ConfigDefaults in the code

