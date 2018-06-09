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
$ git clone https://github.com/sbaresearch/cps-twinning.git
$ cd cps-twinning
$ virtualenv env
$ source env/bin/activate
(env)$ pip install -r requirements.txt
(env)$ pip install .
```

## Usage

Now, to start CPS Twinning, run `make twinning`. The generation of digital twins from an [AutomationML](https://www.automationml.org) artifact can be initiated by executing `twinning <path_to_aml>`. An exemplary specification can be found at `misc/specification/ConveyorSystem.aml`.

Note that this project is only a proof of concept. As a consequence, there are currently many areas that need improvements. In particular, the functionality of the AutomationML parser is currently limited and may require manual adjustments.
	
## How to Cite
If you use CPS Twinning in your research, please cite our [CPSS '18](http://doi.acm.org/10.1145/3198458.3198464) publication. Feel free to use the following BibTeX:

```
@InProceedings{Eckhart2018,
  author    = {Eckhart, Matthias and Ekelhart, Andreas},
  title     = {Towards Security-Aware Virtual Environments for Digital Twins},
  booktitle = {Proceedings of the 4th ACM Workshop on Cyber-Physical System Security},
  year      = {2018},
  series    = {CPSS '18},
  pages     = {61--72},
  address   = {New York, NY, USA},
  publisher = {ACM},
  abstract  = {Digital twins open up new possibilities in terms of monitoring, simulating, optimizing and predicting the state of cyber-physical systems (CPSs). Furthermore, we argue that a fully functional, virtual replica of a CPS can also play an important role in securing the system. In this work, we present a framework that allows users to create and execute digital twins, closely matching their physical counterparts. We focus on a novel approach to automatically generate the virtual environment from specification, taking advantage of engineering data exchange formats. From a security perspective, an identical (in terms of the system's specification), simulated environment can be freely explored and tested by security professionals, without risking negative impacts on live systems. Going a step further, security modules on top of the framework support security analysts in monitoring the current state of CPSs. We demonstrate the viability of the framework in a proof of concept, including the automated generation of digital twins and the monitoring of security and safety rules.},
  acmid     = {3198464},
  doi       = {10.1145/3198458.3198464},
  isbn      = {978-1-4503-5755-5},
  keywords  = {automationml, cyber-physical systems, digital twin, industrial control systems, security monitoring, simulation},
  location  = {Incheon, Republic of Korea},
  numpages  = {12},
  url       = {http://doi.acm.org/10.1145/3198458.3198464},
}
```
