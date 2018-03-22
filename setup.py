from setuptools import setup
from setuptools import find_packages

with open_local(['README.rst']) as rm:
	long_description = rm.read()

setup(
	name='asab',
	version='18.03-beta1',
	description='ASAB simplifies a development of async application servers',
	long_description=long_description,
	url='https://github.com/TeskaLabs/asab',
	author='TeskaLabs Ltd',
	author_email='info@teskalabs.com',
	license='BSD License',
	platforms='any',
	classifiers=[
		'Development Status :: 4 - Beta',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6',
	],
	keywords='asyncio',
	packages=find_packages(exclude=['module_sample']),
	project_urls={
		'Source': 'https://github.com/TeskaLabs/asab'
	},
)

