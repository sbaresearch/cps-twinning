#!/usr/bin/env python

import re
import os
import pkgutil
import time
import logging

logger = logging.getLogger(__name__)

# Regex pattern of located variable declarations
located_vars_pattern_obj = re.compile(r'__LOCATED_VAR\(([a-zA-Z]+),([_a-zA-Z0-9]+),.*\)')
# Regex pattern of program placeholder
prog_placeholder_pattern_obj = re.compile(r'\/\/\sPROGRAM', re.M)
# Regex pattern of vars placeholder
vars_placeholder_pattern_obj = re.compile(r'\/\/\sPLC_VARS', re.M)
# Regex pattern of TMPBASE key
tmp_base_mkfile_pattern_obj = re.compile(r'TMPBASE=(.*)')
# Regex pattern of DSTDIR key
dst_dir_mkfile_pattern_obj = re.compile(r'DSTDIR=(.*)')
# Regex pattern of program comment
programs_pattern_obj = re.compile(r'\/\/\sPrograms')
# Regex pattern of variables comment
variables_pattern_obj = re.compile(r'\/\/\sVariables')


class UnknownPlcTagException(Exception):
    pass


class NotSupportedPlcTagTypeException(Exception):
    pass


class NotSupportedPlcTagClassException(Exception):
    pass


class ModbusTables(object):
    CO = "co"
    DI = "di"
    HR = "hr"
    IR = "ir"

    def __setattr__(self, *_):
        pass


def get_tmp_base_path_from_mkfile():
    # Open Makefile
    mk_file_path = os.path.join(get_pkg_path(), 'plcruntime/Makefile')
    with open(mk_file_path) as f:
        for line in f:
            line = line.rstrip()
            match_tmp_base = tmp_base_mkfile_pattern_obj.match(line)
            if match_tmp_base:
                return match_tmp_base.group(1)


def get_dstdir_path_from_mkfile(plc_name):
    # Open Makefile
    mk_file_path = os.path.join(get_pkg_path(), 'plcruntime/Makefile')
    tmp_base = None
    dst_path_value = None
    with open(mk_file_path) as f:
        for line in f:
            line = line.rstrip()
            match_tmp_base = tmp_base_mkfile_pattern_obj.match(line)
            if match_tmp_base:
                tmp_base = match_tmp_base.group(1)
                continue
            if tmp_base:
                match_dst_dir = dst_dir_mkfile_pattern_obj.match(line)
                if match_dst_dir:
                    dst_path_value = match_dst_dir.group(1)
                    break
    if not tmp_base:
        exit("ERROR: Could not retrieve 'TMPBASE' value from '{}'.\n".format(mk_file_path))
    elif not dst_path_value:
        exit("ERROR: Could not retrieve 'DSTDIR' value from '{}'.\n".format(mk_file_path))
    else:
        # Build up destination dir from tmp base & PLC name
        return dst_path_value.replace("$(TMPBASE)", tmp_base).replace("$(PLCNAME)", plc_name)


def get_pkg_path():
    pkg = pkgutil.get_loader("cpstwinning")
    if pkg is None:
        print "WARNING: Pre-preprocessor uses relative parent path - instead of absolute package file path - as base.\n"
        return '../'
    else:
        return pkg.filename


def filter_vars_csv_section(pattern, lines):
    matched = False
    for line in lines:
        if matched:
            l = line.strip()
            if l:
                yield l
            else:
                break
        else:
            match = pattern.match(line)
            if match:
                matched = True


# Cf. https://stackoverflow.com/a/5998359/5107545
def current_ms():
    return int(round(time.time() * 1000))


# Cf. https://stackoverflow.com/a/11233293/5107545
def setup_logger(name, log_file, formatter, level=logging.WARNING):
    """Method that is used for setting up multiple loggers."""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(level)
    log.addHandler(handler)

    return log
