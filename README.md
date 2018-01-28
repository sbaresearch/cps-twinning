# CPS Twinning

CPS Twinning is a framework for generating and executing digital twins that mirror cyber-physical systems (CPSs).

## Installation

CPS Twinning depends on [Mininet](http://mininet.org) and [MatIEC](https://bitbucket.org/mjsousa/matiec).

### Mininet

To install Mininet, follow the instructions provided by the [Mininet installation guide](http://mininet.org/download/).

### MatIEC

First, install the MatIEC dependencies flex and bison.
For example:
```
$ sudo apt-get update
$ sudo apt-get install flex
$ sudo apt-get install bison	
```
	
Then, clone the MatIEC repository and build the two transcompilers:
```
$ hg clone ssh://hg@bitbucket.org/mjsousa/matiec
$ cd matiec
$ autoreconf -i
$ ./configure
$ make
```

After that, set the following environment variables:
```
$ export MATIEC_INCLUDE_PATH=/home/<user>/matiec/lib
$ export MATIEC_C_INCLUDE_PATH=/home/<user>/matiec/lib/C
$ export PATH=/home/<user>/matiec:$PATH
```

### CPS Twinning

Finally, clone this repository and install CPS Twinning:
```
$ git clone https://github.com/cps-twinning/cps-twinning.git
$ cd cps-twinning
$ virtualenv env
$ source env/bin/activate
(env)$ pip install .	
```

## Usage

Now, to start CPS Twinning, run `make twinning`. The generation of digital twins from an [AutomationML](https://www.automationml.org) artifact can be initiated by executing `twinning <path_to_aml>`. An exemplary specification can be found at `misc/specification/ConveyorSystem.aml`.

Note that this project is only a proof of concept. As a consequence, there are currently many areas that need improvements. In particular, the functionality of the AutomationML parser is currently limited and may require manual adjustments.
	

