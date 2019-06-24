# CPS Twinning

CPS Twinning is a framework for generating and executing digital twins that mirror cyber-physical systems (CPSs). This framework allows to automatically generate virtual environments for digital twins completely from specification. Ideally, artifacts that specify the correct behavior of a CPS have already been created during the production system engineering (PSE) process and will be maintained throughout the entire lifecycle. Standardized engineering data exchange formats, such as AutomationML (AML), may facilitate this process.

On top of CPS Twinning, multiple use cases can be implemented, ranging from behavior-specification-based intrusion detection to behavior learning & analytics.

## Installation

CPS Twinning depends on [Mininet-WiFi](https://github.com/MatthiasEckhart/mininet-wifi), [MatIEC](https://bitbucket.org/mjsousa/matiec) and [CPS State Replication](https://github.com/sbaresearch/cps-state-replication).

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

### CPS State Replication

To install CPS State Replication, follow the instructions provided in the [README](https://github.com/sbaresearch/cps-state-replication/blob/master/README.md).

### CPS Twinning

Finally, clone this repository and install CPS Twinning:
```
$ git clone https://github.com/sbaresearch/cps-twinning.git
$ cd cps-twinning
$ virtualenv env
$ source env/bin/activate
(env)$ pip install -r requirements.txt
(env)$ pip install .
```

## Usage

Now, to start CPS Twinning, run `make twinning`. The generation of digital twins from an [AutomationML](https://www.automationml.org) artifact can be initiated by executing `twinning <path_to_aml>`. An exemplary specification can be found at `misc/specification/CandyFactory.aml`.

Note that this project is only a proof of concept. As a consequence, there are currently many areas that need improvements. In particular, the functionality of the AutomationML parser is currently limited and may require manual adjustments.
	
## How to Cite

If you use CPS Twinning in your research, please consider citing our [CPSS '18](http://doi.acm.org/10.1145/3198458.3198464) publication. Feel free to use the paper's [BibTeX entry](misc/Eckhart2018.bib).
