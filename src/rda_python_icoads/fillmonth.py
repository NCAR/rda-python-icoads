#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillmonth
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/03/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class FillMonth
#   Purpose : process ICOADS monthly data file in IMMA1 format and fill into IVADDB
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from os import path as op
from rda_python_common.pg_util import PgUtil

class FillMonth(PgUtil):

   def __init__(self):
      super().__init__()
      self.CMDS = {
         'filename' : "IMMA1_R3.0.2_",
         'fillicoads' : "fillicoads -i ",
         'fillitable' : "fillitable -t -v dck pt sid -r ",
         'cdmsmonth' : "cdmsmonth "
      }

   #
   # main function to run dsarch
   #
   def main(self):

      argv = sys.argv[1:]
      smonth = srange = None

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif not smonth:
            ms = re.match(r'^(\d+)-(\d+)', arg)
            if ms:
               smonth = "{:04}-{:02}".format(int(ms.group(1)), int(ms.group(2)))
               srange = "{}-01 {}".format(smonth, self.enddate(smonth, 0, 'M'))
            else:
               self.pglog(arg +": Invalid month format", self.LGWNEX)
         else:
            self.pglog("{}: Month is given alreay as '{}'".format(arg, smonth), self.LGWNEX)

      if not smonth:
         print("Usage: fillmonth ProcessMonth")
         print("   Provide a month (YYYY-MM), to fill monthly IMMA1 into IVADDB")
         sys.exit(0)

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("fillmonth {}".format(' '.join(argv)))
      self.fill_monthly_data(smonth, srange)
      self.cmdlog()
      sys.exit(0)

   #
   # fill monthly IMMA1 data to IVADDB
   #
   def fill_monthly_data(self, smonth, srange):

      file = self.CMDS['filename'] + smonth

      if not op.isfile(file):
         # unzip file
         cmd = "gunzip {}.gz".format(file)
         self.pgsystem(cmd, self.LGWNEX, 5)

      # fillicoads
      cmd = self.CMDS['fillicoads'] + file
      self.pgsystem(cmd, self.LGWNEX, 5)

      # zip file
      cmd = "gzip " + file
      self.pgsystem(cmd, self.LGWNEX, 5)

      # fillitable
      cmd = self.CMDS['fillitable'] + srange
      self.pgsystem(cmd, self.LOGWRN, 5)

      # cdmsmonth
#      cmd = self.CMDS['cdmsmonth'] + smonth
#      self.pgsystem(cmd, self.LOGWRN, 5)

# main function to execute this script
def main():
   FillMonth().main()

# call main() to start program
if __name__ == "__main__": main()
