#!/usr/bin/env python3
import json
import argparse
import datetime
import subprocess


def create_manifest(args):
	manifest = {
		'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
	}

	gitr = subprocess.run(["git", "describe", "--abbrev=7", "--tags", "--dirty", "--always"], capture_output=True)
	if gitr.returncode == 0:
		manifest['version'] = gitr.stdout.decode('ascii').strip()
	else:
		pass	
		# TODO: Print warning if returncode is not 0

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
