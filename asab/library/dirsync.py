import os
import shutil
import filecmp


def synchronize_dirs(target, source):
	'''
	Synchronizes 'source' directory into 'target' directory.
	The 'source' directory remains unchanged.

	1. Recursively walk through the "source" directory and compare files with the "target".
	2. If a file exists in "source" but not in "target", copy it.
	3. If a file exists in both but has been modified in "source", copy it to overwrite the one in "target".
	4. If a directory or file exists in "target" but not in "source", remove it.
	'''

	# Ensure target directory exists
	if not os.path.exists(target):
		os.makedirs(target)

	# Step 1: Recursively copy files from source to target
	for dirpath, dirnames, filenames in os.walk(source):
		# Compute relative path to the source base
		relpath = os.path.relpath(dirpath, source)
		target_dir = os.path.join(target, relpath)

		# Create directories in target if they don't exist
		if not os.path.exists(target_dir):
			os.makedirs(target_dir)

		# Check files and synchronize
		for filename in filenames:
			source_file = os.path.join(dirpath, filename)
			target_file = os.path.join(target_dir, filename)
			# Copy if the file doesn't exist in target or if it's modified
			if not os.path.exists(target_file) or not filecmp.cmp(source_file, target_file, shallow=False):
				shutil.copy2(source_file, target_file)

	# Step 2: Recursively delete files/folders in target that don't exist in source
	for dirpath, dirnames, filenames in os.walk(target, topdown=False):  # topdown=False for depth-first
		relpath = os.path.relpath(dirpath, target)
		source_dir = os.path.join(source, relpath)

		# Skip the 'new' directory in the target
		if os.path.normpath(dirpath) == os.path.normpath(os.path.join(target, 'new')):
			continue

		# Check and remove files not in source
		for filename in filenames:
			target_file = os.path.join(dirpath, filename)
			source_file = os.path.join(source_dir, filename)

			# Do not remove if the file is in the 'new' directory
			if 'new' not in os.path.relpath(target_file, target).split(os.path.sep):
				if not os.path.exists(source_file):
					os.remove(target_file)

		# Check and remove directories not in source
		for dirname in dirnames:
			target_subdir = os.path.join(dirpath, dirname)
			source_subdir = os.path.join(source_dir, dirname)

			# Do not remove the 'new' directory or its subdirectories
			if 'new' in os.path.relpath(target_subdir, target).split(os.path.sep):
				continue

			if not os.path.exists(source_subdir):
				shutil.rmtree(target_subdir)
