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
#             2026-09-09 fill each missing month, in order, up to the given month
#   Purpose : process ICOADS monthly data file in IMMA1 format and fill into IVADDB
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from os import path as op
from rda_python_common.pg_util import PgUtil
from rda_python_common.pg_dbi import PgDBI

class FillMonth(PgUtil, PgDBI):

   def __init__(self):
      super().__init__()
      self.CMDS = {
         'filenames' : ["IMMA1_R3.0.2_", "IMMA1_R3.0.3_"],   # IMMA1_R3.0.3_ since 2025-08
         'fillicoads' : "fillicoads -i ",
         'fillitable' : "fillitable -t -v dck pt sid -r ",
         'cdmsmonth' : "cdmsmonth ",
         'inventory' : "cntldb.inventory"
      }

   #
   # main function to run dsarch
   #
   def main(self):

      argv = sys.argv[1:]
      smonth = None

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif not smonth:
            ms = re.match(r'^(\d+)-(\d+)', arg)
            if ms:
               smonth = "{:04}-{:02}".format(int(ms.group(1)), int(ms.group(2)))
            else:
               self.pglog(arg +": Invalid month format", self.LGWNEX)
         else:
            self.pglog("{}: Month is given alreay as '{}'".format(arg, smonth), self.LGWNEX)

      if not smonth:
         print("Usage: fillmonth ProcessMonth")
         print("   Provide a month (YYYY-MM), to fill monthly IMMA1 into IVADDB")
         print("   Any earlier month not filled up yet is filled first, in order")
         sys.exit(0)

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.ivaddb_dbname()
      self.cmdlog("fillmonth {}".format(' '.join(argv)))
      months = self.get_fill_months(smonth)
      if len(months) > 1:
         self.pglog("> {}: fill {} months, {} through {}, in order".format(
                    smonth, len(months), months[0][0], months[-1][0]), self.LOGWRN)
      mcnt = len(months)
      for i in range(mcnt):
         (cmonth, bdate, edate) = months[i]
         self.fill_monthly_data(cmonth, "{} {}".format(bdate, edate))
         if self.month_filled(cmonth, edate) or (i + 1) == mcnt: continue
         # a later month cannot be filled while this one is short of dates
         self.pglog("> {}: filled partially, stop before {}".format(cmonth, months[i+1][0]), self.LOGWRN)
         break
      self.cmdlog()
      sys.exit(0)

   #
   # the iidx values are allocated sequentially, so every month between the last filled date
   # and the given month must be filled, in order; return a [month, bdate, edate] per month,
   # with bdate on the first month set to resume a partially filled month
   #
   def get_fill_months(self, smonth):

      edate = self.enddate(smonth, 0, 'M')
      pgrec = self.pgget(self.CMDS['inventory'], "max(date) mdate", "", self.LGEREX)
      mdate = self.format_date(pgrec['mdate']) if pgrec and pgrec['mdate'] else None
      if not mdate: return [[smonth, smonth + "-01", edate]]   # nothing filled yet

      bdate = self.adddate(mdate, 0, 0, 1)   # resume the partial month, or start the next one
      if self.diffdate(bdate, edate) > 0: return [[smonth, smonth + "-01", edate]]   # refill an earlier month

      months = []
      while self.diffdate(bdate, edate) <= 0:
         cmonth = bdate[0:7]
         cedate = self.enddate(cmonth, 0, 'M')
         if self.diffdate(cedate, edate) > 0: cedate = edate
         months.append([cmonth, bdate, cedate])
         bdate = self.adddate(cedate, 0, 0, 1)

      return months

   #
   # check if the given month is filled through its last date
   #
   def month_filled(self, cmonth, edate):

      pgrec = self.pgget(self.CMDS['inventory'], "max(date) mdate",
                         "date BETWEEN '{}-01' AND '{}'".format(cmonth, edate), self.LGEREX)

      return (pgrec and pgrec['mdate'] and self.format_date(pgrec['mdate']) == edate)

   #
   # locate the monthly IMMA1 file, gunzip it if only the gzipped one is on file
   #
   def get_monthly_file(self, smonth):

      files = [fname + smonth for fname in self.CMDS['filenames']]

      for file in files:
         if op.isfile(file): return file

      for file in files:
         zfile = file + ".gz"
         if op.isfile(zfile):
            self.pgsystem("gunzip " + zfile, self.LGEREX, 5)
            return file

      self.pglog("Miss monthly IMMA1 file, gzipped or not, in {}: {}".format(
                 op.abspath('.'), ', '.join(files)), self.LGEREX)

   #
   # fill monthly IMMA1 data to IVADDB
   #
   def fill_monthly_data(self, smonth, srange):

      file = self.get_monthly_file(smonth)

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
