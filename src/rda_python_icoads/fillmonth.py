#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillmonth
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/03/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : process ICOADS monthly data file in IMMA1 format and fill into IVADDB
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from os import path as op
from rda_python_common import PgLOG
from rda_python_common import PgUtil

CMDS = {
   'filename' : "IMMA1_R3.0.2_",
   'fillicoads' : "fillicoads -i ",
   'fillitable' : "fillitable -t -v dck pt sid -r ",
   'cdmsmonth' : "cdmsmonth "
}

#
# main function to run dsarch
#
def main():

   argv = sys.argv[1:]
   smonth = srange = None

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif not smonth:
         ms = re.match(r'^(\d+)-(\d+)', arg)
         if ms:
            smonth = "{:04}-{:02}".format(int(ms.group(1)), int(ms.group(2)))
            srange = "{}-01 {}".format(smonth, PgUtil.enddate(smonth, 0, 'M'))
         else:
            PgLOG.pglog(arg +": Invalid month format", PgLOG.LGWNEX)
      else:
         PgLOG.pglog("{}: Month is given alreay as '{}'".format(arg, smonth), PgLOG.LGWNEX)

   if not smonth:
      print("Usage: fillmonth ProcessMonth")
      print("   Provide a month (YYYY-MM), to fill monthly IMMA1 into IVADDB")
      sys.exit(0)
   
   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("fillmonth {}".format(' '.join(argv)))
   fill_monthly_data(smonth, srange)
   PgLOG.cmdlog()
   sys.exit(0)

#
# fill monthly IMMA1 data to IVADDB
#
def fill_monthly_data(smonth, srange):
   
   file = CMDS['filename'] + smonth

   if not op.isfile(file):
      # unzip file
      cmd = "gunzip {}.gz".format(file)
      PgLOG.pgsystem(cmd, PgLOG.LGWNEX, 5)

   # fillicoads
   cmd = CMDS['fillicoads'] + file
   PgLOG.pgsystem(cmd, PgLOG.LGWNEX, 5)

   # zip file
   cmd = "gzip " + file
   PgLOG.pgsystem(cmd, PgLOG.LGWNEX, 5)

   # fillitable
   cmd = CMDS['fillitable'] + srange
   PgLOG.pgsystem(cmd, PgLOG.LOGWRN, 5)

   # cdmsmonth
#   cmd = CMDS['cdmsmonth'] + smonth
#   PgLOG.pgsystem(cmd, PgLOG.LOGWRN, 5)

#
# call main() to start program
#
if __name__ == "__main__": main()
