#!/usr/bin/env python2
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

# NOTE: https://packaging.python.org/
setup(
    name='cpstwinning',
    version='0.2',
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
        'lxml==4.9.1',
        'six==1.11.0',  # Dependency of pymodbus
        'pymodbus==1.4.0',
        'scapy==2.4.3',
        'kafka-python==1.4.0',
        'paho-mqtt==1.3.1'
    ],
    package_data={},
    data_files=None,
    scripts=[],
    include_package_data=True,
)
