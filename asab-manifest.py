#!/usr/bin/env python3
import sys
import json
import argparse
import datetime
import subprocess


"""
The purpose of this script is to generate a MANIFEST.json and populate it with container creation time
and the version of the service running in the container. The MANIFEST.json is produced during the creation 
of docker image. When the MANIFEST.json is populated it could look something similar to illustration below 
when generated the help of the current script.

{
		'created_at': 2022-03-21T15:49:37.14000,
		'version' :v22.9-4
}

"""

def create_manifest(args):
	manifest = {
		'created_at': datetime.datetime.utcnow().isoformat() + 'Z',  # This is OK, no tzinfo needed
	}

	try:
		gitr = subprocess.run(["git", "describe", "--abbrev=7", "--tags", "--dirty", "--always"], capture_output=True)
	except FileNotFoundError:
		print("FAILED: Command 'git' not found")
		sys.exit(1)

	if gitr.returncode == 0:
		manifest['version'] = gitr.stdout.decode('ascii').strip()
	else:
		print("FAILED: Command 'git' responded with {}\n{}\n{}".format(
			gitr.returncode,
			gitr.stdout.decode('ascii'),
			gitr.stderr.decode('ascii')
		))
		sys.exit(1)

	with open(args.manifest, "w") as f:
		json.dump(manifest, f, indent='\t')

	print("{} created successfully".format(args.manifest))


def main():
	parser = argparse.ArgumentParser(description='Create MANIFEST.json file')
	parser.add_argument('manifest', metavar='MANIFEST', type=str, help='Location of the MANIFEST.json file')

	args = parser.parse_args()
	create_manifest(args)


if __name__ == '__main__':
	main()
