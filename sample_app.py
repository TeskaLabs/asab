#!/usr/bin/env python3
import sys
import asab

###

class SampleApplication(asab.Application):
	pass

###

if __name__ == '__main__':
	app = SampleApplication()
	ret = app.run()
	sys.exit(ret)