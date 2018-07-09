from constants import LOG_FILE_LOC, LOG_LEVEL, LOG_FORMAT, LOG_DATEFMT

import logging

logging.basicConfig(filename=LOG_FILE_LOC, level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATEFMT)
