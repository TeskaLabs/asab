#!/usr/bin/env python3
import os
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

```
{
	"created_at": "2022-03-21T15:49:37.14000",
	"version": "v22.04"
}
```

If GitLab CI/CD is configured properly, additional infomation can be included:

```
{
	"created_at": "2023-02-20T20:00:37.022980Z",
	"version": "v23.08-alpha2",
	"CI_COMMIT_BRANCH": "master",
	"CI_COMMIT_REF_NAME": "master",
	"CI_COMMIT_SHA": "dae2cfa8f7d4769375e73499c4aaffea727f8501",
	"CI_COMMIT_TIMESTAMP": "2023-02-20T20:57:59+01:00",
	"CI_JOB_ID": "30420",
	"CI_PIPELINE_CREATED_AT": "2023-02-20T19:58:06Z",
	"CI_RUNNER_ID": "54",
	"CI_RUNNER_EXECUTABLE_ARCH": "linux/amd64"
}
```

"""

# List of environment variables to be included in the MANIFEST.json
envvars = [
	"CI_COMMIT_BRANCH",
	"CI_COMMIT_TAG",
	"CI_COMMIT_REF_NAME",
	"CI_COMMIT_SHA",
	"CI_COMMIT_TIMESTAMP",
	"CI_JOB_ID",
	"CI_PIPELINE_CREATED_AT",
	"CI_RUNNER_ID",
	"CI_RUNNER_EXECUTABLE_ARCH",
	"GITHUB_HEAD_REF",
	"GITHUB_JOB",
	"GITHUB_SHA",
	"GITHUB_REPOSITORY",
]


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

	for envvar in envvars:
		envvarvalue = os.environ.get(envvar)
		if envvarvalue is not None:
			manifest[envvar] = envvarvalue

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
