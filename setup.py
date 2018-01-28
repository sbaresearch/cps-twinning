#!/usr/bin/env python2
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

# NOTE: https://packaging.python.org/
setup(
    name='cpstwinning',
    version='0.1',
    description='',
    # NOTE: long_description displayed on PyPi
    long_description='',
    url='',
    author='',
    author_email='',
    license='',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
	'Intended Audience :: Science/Research',
	'Intended Audience :: Manufacturing',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Education',
        'Topic :: Security',
	'Topic :: System :: Emulators',
    ],
    keywords='cps security',
    packages=find_packages(),
    install_requires=[
        'lxml==3.4.2',
        'six==1.11.0',  # Dependency of pymodbus
        'pymodbus==1.4.0',
    ],
    package_data={},
    data_files=None,
    scripts=[],
    include_package_data=True,
)

