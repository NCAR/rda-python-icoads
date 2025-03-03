#!/usr/bin/env python3
#
##################################################################################
#
#     Title : cleanicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : clean up one or all IMMA1 attms in IVADDB for given period
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from rda_python_common import PgLOG
from rda_python_common import PgDBI
from rda_python_common import PgUtil
from . import PgIMMA

PVALS = {
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
def main():

   option = ''
   files = []
   leaduid = 0
   chkexist = 0
   readall = 0
   argv = sys.argv[1:]

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-a":
         option = 'a'
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         PVALS['aname'] = arg
         option = ''
      elif not PVALS['bdate']:
         PVALS['bdate'] = arg
      elif not PVALS['edate']:
         PVALS['edate'] = arg
      else:
         PgLOG.pglog(arg + ": Invalid parameter", PgLOG.LGWNEX)

   if not PVALS['bdate']:
      print("Usage: cleanicoads [-a ATTNAME] BDATE EDATE")
      print("   Option -a - clean a single attm for given attm name")
      PgLOG.pgexit()

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
   PgLOG.cmdlog("cleanicoads {}".format(' '.join(argv)))
   set_table_info()
   clean_imma_data()   
   PgLOG.cmdlog()
   PgLOG.pgexit()

#
# set the table index list
#
def set_table_info():

   table = "cntldb.inventory"
   if PVALS['edate']:
      PVALS['dcnd'] = "date BETWEEN '{}' AND '{}'".format(PVALS['bdate'], PVALS['edate'])
   else:
      PVALS['dcnd'] = "date >= '{}'".format(PVALS['bdate'])

   PVALS['tinfo'] = PgDBI.pgmget(table, "tidx, min(miniidx) bidx, max(maxiidx) eidx", PVALS['dcnd'] + " GROUP BY tidx", PgLOG.LGEREX)
   PVALS['tcnt'] = len(PVALS['tinfo']['tidx']) if PVALS['tinfo'] else 0

   if not PVALS['tcnt']:
      PgLOG.pglog("{}: No data found in IVADDB for {}".format(table, PVALS['dcnd']), PgLOG.LGEREX)   

#
# clean up imma data
#
def clean_imma_data():

   table = "cntldb.inventory"

   for i in range(PVALS['tcnt']):
      tidx = PVALS['tinfo']['tidx'][i]
      cnd = "iidx BETWEEN {} AND {}".format(PVALS['tinfo']['bidx'][i], PVALS['tinfo']['eidx'][i])
      if PVALS['aname']:
         clean_one_attm_for_tidx(PVALS['aname'], tidx, cnd)
      else:
         clean_imma_data_for_tidx(tidx, cnd)

   cnt = PgDBI.pgdel(table, PVALS['dcnd'], PgLOG.LGEREX)
   s = 's' if cnt > 1 else ''
   PgLOG.pglog("{}: {} record{} deleted for {}".format(table, cnt, s, PVALS['dcnd']), PgLOG.LOGWRN)

#
# clean up imma data for table index
#
def clean_imma_data_for_tidx(tidx, cnd):

   PgLOG.pglog("Clean IMMA data for table index {}...".format(tidx), PgLOG.LOGWRN)

   for i in range(PgIMMA.TABLECOUNT):
      aname = PgIMMA.IMMA_NAMES[i]
      clean_one_attm_for_tidx(aname, tidx, cnd)

#
# clean up one attm data for table index
#
def clean_one_attm_for_tidx(aname, tidx, cnd):

   table = "{}_{}".format(aname, tidx)
   if not PgDBI.pgcheck(table): return 0  # not record to delete

   if aname == 'iuida': clean_itidx_for_tidx(table, cnd) 

   cnt = PgDBI.pgdel(table, cnd, PgLOG.LGEREX)
   s = 's' if cnt > 1 else ''
   PgLOG.pglog("{}: {} record{} deleted for {}".format(table, cnt, s, cnd), PgLOG.LOGWRN)

   cnt = PgDBI.pgget(table, "", "", PgLOG.LGEREX)
   clean_iattm_for_tidx(aname, tidx, cnt)

#
# clean up table itidx for table index
#
def clean_itidx_for_tidx(table, cnd):

   tname = "cntldb.itidx"
   uids = PgDBI.pgmget(table, "distinct (substring(uid, 1, 2)) uida", cnd, PgLOG.LGEREX)
   ucnt = len(uids['uida']) if uids else 0
   for i in range(ucnt):
      table = "{}_{}".format(tname, uids['uida'][i].lower())
      if not PgDBI.pgcheck(table): continue
      cnt = PgDBI.pgdel(table, cnd, PgLOG.LOGWRN)
      s = 's' if cnt > 1 else ''
      PgLOG.pglog("{}: {} record{} deleted".format(table, cnt, s), PgLOG.LOGWRN)

#
# clean up table iattm for table index
#
def clean_iattm_for_tidx(aname, tidx, cnt):

   table = "cntldb.iattm"
   cnd = "attm = '{}' AND tidx = {}".format(aname, tidx)
   pgrec = {'count' : cnt}
   PgDBI.pgupdt(table, pgrec, cnd, PgLOG.LGWNEX)
   PgLOG.pglog("{}: Set count to {} for {}".format(table, cnt, cnd), PgLOG.LOGWRN)
   
   table += "_daily"
   cnd += " AND " + PVALS['dcnd']
   PgDBI.pgdel(table, PVALS['dcnd'], PgLOG.LGWNEX)

#
# call main() to start program
#
if __name__ == "__main__": main()
