#!/usr/bin/env python3
#
##################################################################################
#
#     Title : writeicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/05/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : read ICOADS data from IVADDB and write out monthly files in IMMA format
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
from rda_python_common import PgSIG
from rda_python_common import PgUtil
from rda_python_common import PgFile
from . import PgIMMA

PVALS = {
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
def main():

   option = ''
   argv = sys.argv[1:]
   
   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-a":
         PVALS['dumpall'] = 1
      elif arg == "-f":
         option = 'f'
      elif arg == "-m":
         option = 'm'
      elif re.match(r'^-', arg):
        PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         if option == 'f':
           PVALS['fnroot'] = arg
         elif option == 'm':
            PVALS['mproc'] = arg
         option = ''
      elif not PVALS['bdate']:
         PVALS['bdate'] = arg
      elif not PVALS['edate']:
         PVALS['edate'] = arg
      else:
        PgLOG.pglog(arg + ": Invalid parameter", PgLOG.LGWNEX)

   PgDBI.ivaddb_dbname()
   
   if not (PVALS['bdate'] and PVALS['edate']):
      pgrec = PgDBI.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', PgLOG.LGEREX)
      print("Usage: writeicoads [-a] [-m mproc] [-f RootFileName] BeginDate EndDate")
      print("   Default RootFileName = {}".format(PVALS['fnroot']))
      print("   Option -a - dump all attms, including multi-line ones, such as IVAD and REANQC")
      print("   Option -m - start up to given number of processes, one for each file dump (Default to 10)")
      print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)

   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate
   
   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("writeicoads {}".format(' '.join(argv)))
   PVALS['names'] = '/'.join(PgIMMA.IMMA_NAMES)
   write_imma_data()
   PgLOG.cmdlog()
   sys.exit(0)

#
# read imma data from IVADB and dump into files
#
def write_imma_data():
   
   mcnt = init_months()

   if mcnt == 1: PVALS['mproc'] = 1
   if PVALS['mproc'] > 1: PgSIG.start_none_daemon('writeicoads', '', PgLOG.PGLOG['CURUID'], PVALS['mproc'], 300, 1)

   for midx in range(mcnt):
      if PVALS['mproc'] > 1:
         stat = PgSIG.start_child("writeicoads_{}".format(midx), PgLOG.LOGWRN, 1)  # try to start a child process
         if stat <= 0:
            sys.exit(1)   # something wrong
         elif PgSIG.PGSIG['PPID'] > 1:
            write_monthly_imma_file(midx)
            sys.exit(0)  # stop child process
         else:
            PgDBI.pgdisconnect(0)  # disconnect database for reconnection
            continue  # continue for next midx
      else:
         write_monthly_imma_file(midx)

   if PVALS['mproc'] > 1: # quit parent without waiting
      PgLOG.pglog("Started {} child processes to write icoads files".format(mcnt), PgLOG.LOGWRN)

#
# read icoads record from given file name and save them into RDADB
#
def write_monthly_imma_file(midx):

   fname = "{}_{}".format(PVALS['fnroot'], PVALS['month'][midx])
   PgLOG.pglog("write IMMA1 records into File '{}' from IVADDB".format(fname), PgLOG.WARNLG)
   opened = 0
   acounts = [0]*PgIMMA.TABLECOUNT
   IMMA = open(fname, 'w')
   cdate = PVALS['bmdate'][midx]
   while cdate <= PVALS['emdate'][midx]:
      acnts = PgIMMA.write_imma_records(IMMA, cdate, 0, PVALS['dumpall'])
      if acnts:
         for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]
      cdate = PgUtil.adddate(cdate, 0, 0, 1)

   IMMA.close()
   if acounts[0] == 0: PgFile.delete_local_file(fname)

   PgLOG.pglog("{}({}) written into {}".format('/'.join(map(str, acounts)), PVALS['names'], fname), PgLOG.LOGWRN)

#
# intialize month arrays
#
def init_months():

   bdate = PVALS['bdate']
   table = "cntldb.inventory"
   mcnt = done = 0
   while True:
      edate = PgUtil.enddate(bdate, 0, 'M')
      if PgUtil.diffdate(PVALS['edate'], edate) <= 0:
         edate = PVALS['edate']
         done = 1
      if PgDBI.pgget(table, "date", "date BETWEEN '{}' AND '{}'".format(bdate, edate), PgLOG.LGEREX):
         PVALS['bmdate'].append(bdate)
         PVALS['month'].append(PgUtil.format_date(bdate, "YYYY-MM"))
         PVALS['emdate'].append(edate)
         mcnt += 1
      if done: break
      bdate = PgUtil.adddate(edate, 0, 0, 1)

   return mcnt

#
# call main() to start program
#
if __name__ == "__main__": main()
