#!/usr/bin/env python3
#
##################################################################################
#
#     Title : cleanicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CleanIcoads
#   Purpose : clean up one or all IMMA1 attms in IVADDB for given period
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class CleanIcoads(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'bdate' : None,
         'edate' : None,
         'aname' : None,
         'tinfo' : {},
         'tcnt' : 0,
         'dcnd' : None,
         'uatti' : '',
         'names' : None
      }

   #
   # main function to run dsarch
   #
   def main(self):

      option = ''
      files = []
      leaduid = 0
      chkexist = 0
      readall = 0
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-a":
            option = 'a'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            self.PVALS['aname'] = arg
            option = ''
         elif not self.PVALS['bdate']:
            self.PVALS['bdate'] = arg
         elif not self.PVALS['edate']:
            self.PVALS['edate'] = arg
         else:
            self.pglog(arg + ": Invalid parameter", self.LGWNEX)

      if not self.PVALS['bdate']:
         print("Usage: cleanicoads [-a ATTNAME] BDATE EDATE")
         print("   Option -a - clean a single attm for given attm name")
         self.pgexit()

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.set_scname(dbname = 'ivaddb', scname = self.IVADSC, lnname = 'ivaddb', dbhost = self.PGLOG['PMISCHOST'])
      self.cmdlog("cleanicoads {}".format(' '.join(argv)))
      self.set_table_info()
      self.clean_imma_data()   
      self.cmdlog()
      self.pgexit()

   #
   # set the table index list
   #
   def set_table_info(self):

      table = f"{self.CNTLSC}.inventory"
      if self.PVALS['edate']:
         self.PVALS['dcnd'] = "date BETWEEN '{}' AND '{}'".format(self.PVALS['bdate'], self.PVALS['edate'])
      else:
         self.PVALS['dcnd'] = "date >= '{}'".format(self.PVALS['bdate'])

      self.PVALS['tinfo'] = self.pgmget(table, "tidx, min(miniidx) bidx, max(maxiidx) eidx", self.PVALS['dcnd'] + " GROUP BY tidx", self.LGEREX)
      self.PVALS['tcnt'] = len(self.PVALS['tinfo']['tidx']) if self.PVALS['tinfo'] else 0

      if not self.PVALS['tcnt']:
         self.pglog("{}: No data found in IVADDB for {}".format(table, self.PVALS['dcnd']), self.LGEREX)   

   #
   # clean up imma data
   #
   def clean_imma_data(self):

      table = f"{self.CNTLSC}.inventory"

      for i in range(self.PVALS['tcnt']):
         tidx = self.PVALS['tinfo']['tidx'][i]
         cnd = "iidx BETWEEN {} AND {}".format(self.PVALS['tinfo']['bidx'][i], self.PVALS['tinfo']['eidx'][i])
         if self.PVALS['aname']:
            self.clean_one_attm_for_tidx(self.PVALS['aname'], tidx, cnd)
         else:
            self.clean_imma_data_for_tidx(tidx, cnd)

      if not self.PVALS['aname']:
         cnt = self.pgdel(table, self.PVALS['dcnd'], self.LGEREX)
         s = 's' if cnt > 1 else ''
         self.pglog("{}: {} record{} deleted for {}".format(table, cnt, s, self.PVALS['dcnd']), self.LOGWRN)

   #
   # clean up imma data for table index
   #
   def clean_imma_data_for_tidx(self, tidx, cnd):

      self.pglog("Clean IMMA data for table index {}...".format(tidx), self.LOGWRN)

      for i in range(self.TABLECOUNT):
         aname = self.IMMA_NAMES[i]
         self.clean_one_attm_for_tidx(aname, tidx, cnd)

   #
   # clean up one attm data for table index
   #
   def clean_one_attm_for_tidx(self, aname, tidx, cnd):

      table = f"{self.IVADSC}.{aname}_{tidx}"
      if not self.pgcheck(table): return 0  # not record to delete

      if aname == 'iuida': self.clean_itidx_for_tidx(table, cnd) 

      cnt = self.pgdel(table, cnd, self.LGEREX)
      s = 's' if cnt > 1 else ''
      self.pglog("{}: {} record{} deleted for {}".format(table, cnt, s, cnd), self.LOGWRN)

      cnt = self.pgget(table, "", "", self.LGEREX)
      self.clean_iattm_for_tidx(aname, tidx, cnt)

   #
   # clean up table itidx for table index
   #
   def clean_itidx_for_tidx(self, table, cnd):

      tname = f"{self.CNTLSC}.itidx"
      uids = self.pgmget(table, "distinct (substring(uid, 1, 2)) uida", cnd, self.LGEREX)
      ucnt = len(uids['uida']) if uids else 0
      for i in range(ucnt):
         table = "{}_{}".format(tname, uids['uida'][i].lower())
         if not self.pgcheck(table): continue
         cnt = self.pgdel(table, cnd, self.LOGWRN)
         s = 's' if cnt > 1 else ''
         self.pglog("{}: {} record{} deleted".format(table, cnt, s), self.LOGWRN)

   #
   # clean up table iattm for table index
   #
   def clean_iattm_for_tidx(self, aname, tidx, cnt):

      table = f"{self.CNTLSC}.iattm"
      cnd = "attm = '{}' AND tidx = {}".format(aname, tidx)
      pgrec = {'count' : cnt}
      self.pgupdt(table, pgrec, cnd, self.LGWNEX)
      self.pglog("{}: Set count to {} for {}".format(table, cnt, cnd), self.LOGWRN)

      table += "_daily"
      cnd += " AND " + self.PVALS['dcnd']
      self.pgdel(table, self.PVALS['dcnd'], self.LGWNEX)

# main function to execute this script
def main():
   CleanIcoads().main()

# call main() to start program
if __name__ == "__main__": main()
