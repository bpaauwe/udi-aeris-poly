#!/usr/bin/env python3
"""
Polyglot v2 node server AERIS weather data
Copyright (C) 2019,2020 Robert Paauwe
"""

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
from nodes import aeris
from nodes import aeris_daily

LOGGER = polyinterface.LOGGER

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('AERIS')
        polyglot.start()
        control = aeris.Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        

