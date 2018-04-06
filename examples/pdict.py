#!/usr/bin/env python3
import os.path
import asab

class MyApplication(asab.Application):

	async def main(self):
		var_dir = asab.Config['general']['var_dir']
		pdict = asab.PersistentDict(os.path.join(var_dir, 'pdict.bin'))

		counter = pdict['counter'] = pdict.setdefault('counter', 0) + 1
		print("Executed for {} times".format(counter))

		self.stop()

if __name__ == '__main__':
	app = MyApplication()
	app.run()
