#!/usr/bin/env python3
import os.path
import asab


class MyApplication(asab.Application):

	async def main(self):
		var_dir = asab.Config['general']['var_dir']
		pdict = asab.PersistentDict(os.path.join(var_dir, 'pdict.bin'))

		# Explicit load
		pdict.load()
		counter = pdict['counter'] = pdict.setdefault('counter', 0) + 1
		print("Executed for {} times".format(counter))

		# Explicit store
		pdict.store()
		self.stop()


if __name__ == '__main__':
	app = MyApplication()
	app.run()
