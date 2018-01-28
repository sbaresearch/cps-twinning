# CPS Twinning makefile

LATEST_VERSION = 0.0.1
MININET = sudo -E mn

PYTHON = sudo -E python
PYTHON_OPTS =

# Twinning

twinning:
	$(PYTHON) $(PYTHON_OPTS) run.py

clean-mininet:
	sudo mn -c

