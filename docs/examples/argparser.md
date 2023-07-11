---
author: Jakub Boukal
commit: c9edd8964b82e5962b9d4eda0ad499ef8845ea83
date: 2020-02-10 14:35:53+01:00
title: Argparser

---

!!! example

	```python title='argparser.py' linenums="1"
	#!/usr/bin/env python3
	import asab
	
	
	class Application(asab.Application):
	
		def __init__(self):
			self.command = None
			self.command_args = None
			super().__init__()
	
	
		def create_argument_parser(self, *args, **kwargs):
			parser = super().create_argument_parser()
	
			subparsers = parser.add_subparsers(dest="command")
			command1_subparser = subparsers.add_parser('command1')
			command1_subparser.add_argument('-i', '--input-file')
	
			command2_subparser = subparsers.add_parser('command2')
			command2_subparser.add_argument('-o', '--output-file')
	
			return parser
	
	
		def parse_arguments(self, args=None):
			args = super().parse_arguments()
			self.command = args.command or ""
	
			if args.command == "command1":
				self.command_args = {
					"input_file": args.input_file or ""
				}
	
			elif args.command == "command2":
				self.command_args = {
					"output_file": args.output_file or ""
				}
	
			return args
	
	
		async def main(self):
	
			if self.command == "":
				exit("Please specify command (run with --help to see your options)")
	
			print("Command: {}; Args: {}".format(self.command, self.command_args))
	
			self.stop()
	
	
	if __name__ == '__main__':
		app = Application()
		app.run()
	
	```
