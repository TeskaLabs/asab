#!/usr/bin/env python3
import sys
import json
import argparse
import datetime
import subprocess


def create_manifest(args):
	manifest = {
		'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
	}

	try:
		gitr = subprocess.run(["git", "describe", "--abbrev=7", "--tags", "--dirty", "--always"], capture_output=True)
	except FileNotFoundError:
		gitr = None
		print("FAILED: Command 'git' not found")
		sys.exit(1)

	if gitr is not None and gitr.returncode == 0:
		manifest['version'] = gitr.stdout.decode('ascii').strip()
	else:
		print("FAILED: Command 'git' responded with {}\n{}\n{}".format(gitr.returncode, gitr.stdout, gitr.strerr))
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
