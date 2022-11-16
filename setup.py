import pathlib
import re
import subprocess

from setuptools.command.build_py import build_py
from setuptools import find_packages
from setuptools import setup

here = pathlib.Path(__file__).parent
txt = (here / 'asab' / '__init__.py').read_text('utf-8')
if (here / '.git').exists():
	# This branch is happening during build from git version
	module_dir = (here / 'asab')

	version = subprocess.check_output(
		['git', 'describe', '--abbrev=7', '--tags', '--dirty=+dirty', '--always'], cwd=module_dir)
	version = version.decode('utf-8').strip()
	if version[:1] == 'v':
		version = version[1:]

	build = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=module_dir)
	build = build.decode('utf-8').strip()

else:
	# This is executed from packaged & distributed version
	txt = (here / 'asab' / '__version__.py').read_text('utf-8')
	version = re.findall(r"^__version__ = '([^']+)'\r?$", txt, re.M)[0]
	build = re.findall(r"^__build__ = '([^']+)'\r?$", txt, re.M)[0]


class custom_build_py(build_py):

	def run(self):
		super().run()

		# This replace content of `__version__.py` in build folder
		version_file_name = pathlib.Path(self.build_lib, 'asab/__version__.py')
		with open(version_file_name, 'w') as f:
			f.write("__version__ = '{}'\n".format(version))
			f.write("__build__ = '{}'\n".format(build))
			f.write("\n")


setup(
	name='asab',
	version=version,
	description='ASAB simplifies a development of async application servers',
	long_description=open('README.rst').read(),
	url='https://github.com/TeskaLabs/asab',
	author='TeskaLabs Ltd',
	author_email='info@teskalabs.com',
	license='BSD License',
	platforms='any',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Programming Language :: Python :: 3.7',
		'Programming Language :: Python :: 3.8',
		'Programming Language :: Python :: 3.9',
		'Programming Language :: Python :: 3.10',
		'Programming Language :: Python :: 3.11',
	],
	keywords='asyncio',
	packages=find_packages(exclude=['module_sample']),
	project_urls={
		'Source': 'https://github.com/TeskaLabs/asab'
	},
	install_requires=[
		'aiohttp>=3.8.3,<4',
		'fastjsonschema>=2.16.2,<3',
		'kazoo>=2.9.0,<3',
		'PyYAML>=6.0,<7'
	],
	extras_require={
		'git': 'pygit2>=1.9.1',
		'storage_encryption': 'cryptography',
	},
	cmdclass={
		'build_py': custom_build_py,
	},
	scripts=[
		'asab-manifest.py'
	],
)
