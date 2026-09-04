#!/usr/bin/env python3
#
##################################################################################
#
#     Title : writeicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/05/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class WriteIcoads
#   Purpose : read ICOADS data from IVADDB and write out monthly files in IMMA format
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class WriteIcoads(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'bdate' : None,
         'edate' : None,
         'month' : [],
         'bmdate' : [],
         'emdate' : [],
         'fnroot' : "IMMA1_R3.0.0",
         'names' : None,
         'mporc' : 10,
         'dumpall' : 0
      }

   #
   # main function to run dsarch
   #
   def main(self):

      option = ''
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-a":
            self.PVALS['dumpall'] = 1
         elif arg == "-f":
            option = 'f'
         elif arg == "-m":
            option = 'm'
         elif re.match(r'^-', arg):
           self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            if option == 'f':
              self.PVALS['fnroot'] = arg
            elif option == 'm':
               self.PVALS['mproc'] = arg
            option = ''
         elif not self.PVALS['bdate']:
            self.PVALS['bdate'] = arg
         elif not self.PVALS['edate']:
            self.PVALS['edate'] = arg
         else:
           self.pglog(arg + ": Invalid parameter", self.LGWNEX)

      self.ivaddb_dbname()

      if not (self.PVALS['bdate'] and self.PVALS['edate']):
         pgrec = self.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', self.LGEREX)
         print("Usage: writeicoads [-a] [-m mproc] [-f RootFileName] BeginDate EndDate")
         print("   Default RootFileName = {}".format(self.PVALS['fnroot']))
         print("   Option -a - dump all attms, including multi-line ones, such as IVAD and REANQC")
         print("   Option -m - start up to given number of processes, one for each file dump (Default to 10)")
         print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("writeicoads {}".format(' '.join(argv)))
      self.PVALS['names'] = '/'.join(self.IMMA_NAMES)
      self.write_imma_data()
      self.cmdlog()
      sys.exit(0)

   #
   # read imma data from IVADB and dump into files
   #
   def write_imma_data(self):

      mcnt = self.init_months()

      if mcnt == 1: self.PVALS['mproc'] = 1
      if self.PVALS['mproc'] > 1: self.start_none_daemon('writeicoads', '', self.PGLOG['CURUID'], self.PVALS['mproc'], 300, 1)

      for midx in range(mcnt):
         if self.PVALS['mproc'] > 1:
            stat = self.start_child("writeicoads_{}".format(midx), self.LOGWRN, 1)  # try to start a child process
            if stat <= 0:
               sys.exit(1)   # something wrong
            elif self.PGSIG['PPID'] > 1:
               self.write_monthly_imma_file(midx)
               sys.exit(0)  # stop child process
            else:
               self.pgdisconnect(0)  # disconnect database for reconnection
               continue  # continue for next midx
         else:
            self.write_monthly_imma_file(midx)

      if self.PVALS['mproc'] > 1: # quit parent without waiting
         self.pglog("Started {} child processes to write icoads files".format(mcnt), self.LOGWRN)

   #
   # read icoads record from given file name and save them into RDADB
   #
   def write_monthly_imma_file(self, midx):

      fname = "{}_{}".format(self.PVALS['fnroot'], self.PVALS['month'][midx])
      self.pglog("write IMMA1 records into File '{}' from IVADDB".format(fname), self.WARNLG)
      opened = 0
      acounts = [0]*self.TABLECOUNT
      IMMA = open(fname, 'w')
      cdate = self.PVALS['bmdate'][midx]
      while cdate <= self.PVALS['emdate'][midx]:
         acnts = self.write_imma_records(IMMA, cdate, 0, self.PVALS['dumpall'])
         if acnts:
            for i in range(self.TABLECOUNT): acounts[i] += acnts[i]
         cdate = self.adddate(cdate, 0, 0, 1)

      IMMA.close()
      if acounts[0] == 0: self.delete_local_file(fname)

      self.pglog("{}({}) written into {}".format('/'.join(map(str, acounts)), self.PVALS['names'], fname), self.LOGWRN)

   #
   # intialize month arrays
   #
   def init_months(self):

      bdate = self.PVALS['bdate']
      table = "cntldb.inventory"
      mcnt = done = 0
      while True:
         edate = self.enddate(bdate, 0, 'M')
         if self.diffdate(self.PVALS['edate'], edate) <= 0:
            edate = self.PVALS['edate']
            done = 1
         if self.pgget(table, "date", "date BETWEEN '{}' AND '{}'".format(bdate, edate), self.LGEREX):
            self.PVALS['bmdate'].append(bdate)
            self.PVALS['month'].append(self.format_date(bdate, "YYYY-MM"))
            self.PVALS['emdate'].append(edate)
            mcnt += 1
         if done: break
         bdate = self.adddate(edate, 0, 0, 1)

      return mcnt

# main function to execute this script
def main():
   WriteIcoads().main()

# call main() to start program
if __name__ == "__main__": main()
