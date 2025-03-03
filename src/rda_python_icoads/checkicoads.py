#!/usr/bin/env python3
#
##################################################################################
#
#     Title : checkicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : check and compare ICOADS data files and IVADDB records
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
from rda_python_common import PgOPT
from rda_python_common import PgSIG
from . import PgIMMA

PVALS = {
   'bdate' : None,
   'edate' : None,
   'bmdate' : [],
   'emdate' : [],
   'fname' : [],
   'flag' : [],   # 1 - file exists, 2 - db records exist, 3 - both
   'mproc' : 10,
   'fpattern' : "IMMA1_R3.0.0_<YYYY-MM>",
   'readall' : 0
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
         PVALS['readall'] = 1
      elif arg == "-f":
         option = 'f'
      elif arg == "-m":
         option = 'm'
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         if option == 'f':
            PVALS['fpattern'] = arg
         elif option == 'm':
            PVALS['mproc'] = arg
         option = ''
      elif not PVALS['bdate']:
         PVALS['bdate'] = arg
      elif not PVALS['edate']:
         PVALS['edate'] = arg
      else:
         PgLOG.pglog(arg + ": Invalid parameter", PgLOG.LGWNEX)
   
   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
   
   if not (PVALS['bdate'] and PVALS['edate']):
      pgrec = PgDBI.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', PgLOG.LGEREX)
      print("Usage: checkicoads [-a] [-m mproc] [-f FilePattern] BeginDate EndDate")
      print("   Default FilePattern is " + PVALS['fpattern'])
      print("   Option -a - read all attms, including multi-line ones, such as IVAD and REANQC")
      print("   Option -m - start up to given number of processes, one for each month (Default to 10)")
      print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)

   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate
   
   PgLOG.cmdlog("checkicoads {}".format(' '.join(argv)))
   check_imma_data()
   PgLOG.cmdlog()
   sys.exit(0)

#
# check imma data
#
def check_imma_data():

   mcnt = init_months()
   if mcnt == 1: PVALS['mproc'] = 1
   if PVALS['mproc'] > 1:
      PgSIG.start_none_daemon('writeicoads', '', PgLOG.PGLOG['CURUID'], PVALS['mproc'], 300, 1)

   for midx in range(mcnt):
      fname = PVALS['fname'][midx]
      if op.isfile(fname +".cnt"): continue    # monthly file counted already
      if PVALS['mproc'] > 1:
         stat = PgSIG.start_child("checkicoads_{}".format(midx), PgLOG.LOGWRN, 1)  # try to start a child process
         if stat <= 0:
            sys.exit(1)   # something wrong
         elif PgSIG.PGSIG['PPID'] > 1:
            check_imma_file(fname, midx)
            sys.exit(0)  # stop child process
         else:
            PgDBI.pgdisconnect(0)  # disconnect database for reconnection
            continue   # continue for next midx
      else:
         check_imma_file(fname, midx)

   if PVALS['mproc'] > 1: PgSIG.check_child(None, 0, PgLOG.LOGWRN, 1)

   dump_final_counts()

#
# compare icoads records from given file name and IVADDB
#
def check_imma_file(fname, midx):

   PgLOG.pglog("Count IMMA records in File '{}'".format(fname), PgLOG.WARNLG)
   flag = PVALS['flag'][midx]

   acnts = [0]*PgIMMA.TABLECOUNT
   acounts = [0]*PgIMMA.TABLECOUNT

   if flag&1:
      IMMA = open(fname, 'r')
      line = IMMA.readline()   
      while line:
         if PVALS['readall'] and re.match(r'^98', line):
             PgIMMA.get_imma_multiple_counts(line, acnts)
         else:
            PgIMMA.get_imma_counts(line, acnts)
         line.IMMA.readline()
      IMMA.close()
      for i in range(PgIMMA.TABLECOUNT): acounts[i] = acnts[i]

   if flag&2:
      PgLOG.pglog("Count IMMA records in in IVADDB", PgLOG.WARNLG)
      cdate = bdate = PVALS['bmdate'][midx]
      edate = PVALS['emdate'][midx]
      while cdate <= edate:
         acnts = PgIMMA.count_imma_records(cdate, 0, PVALS['readall'])
         cdate = PgUtil.adddate(cdate, 0, 0, 1)
         if acnts:
            for i in range(PgIMMA.TABLECOUNT): acounts[i] -= acnts[i]

   dump_monthly_counts(fname, acounts)

#
# dump monthly counts
#
def dump_monthly_counts(fname, acounts):

   oname = fname + ".cnt"
   IMMA = open(oname, 'w')
   IMMA.write("{}, {}\n".format(fname, ', '.join(acounts)))
   IMMA.close()

#
# concat all monthly counts into one
#
def dump_final_counts():

   fname = "ICOADS_DIFF_COUNTS.csv"

   IMMA = open(fname, 'w')
   IMMA.write("FileName, {}\n".format(', '.join(PgIMMA.IMMA_NAMES)))
   IMMA.close()
   PgLOG.pgsystem("cat *.cnt >> " + fname)

#
# initialize the month list
#
def init_months():

   seps = ["<" , ">"];  # temporal pattern delimiters
   match = "[^" + seps[1] + "]+"

   ms = re.search(r'{}({}){}'.format(seps[0], match, seps[1]), PVALS['fpattern'])
   if ms:
      tpattern = ms.group(1)
      treplace = "{}{}{}".format(seps[0], tpattern, seps[1])
   else:
      PgLOG.pglog(PVALS['fpattern'] + ": Not temporal pattern found to get month list", PgLOG.LGEREX)

   bdate = PVALS['bdate']
   done = midx = 0
   while True:
      edate = PgUtil.enddate(bdate, 0, 'M')
      if PgUtil.diffdate(PVALS['edate'], edate) <= 0:
         edate = PVALS['edate']
         done = 1
      mdate = PgUtil.format_date(bdate, tpattern)
      fname = PVALS['fpattern'].replace(treplace, mdate)
      flag = 0
      if op.isfile(fname): flag += 1
      if PgDBI.pgget("cntldb.inventory", "", "date BETWEEN '{}' AND '{}'".format(bdate, edate), PgLOG.LGEREX):
         flag += 2
      if flag:
         PVALS['bmdate'].append(bdate)
         PVALS['emdate'].append(edate)
         PVALS['fname'].append(fname)
         PVALS['flag'].append(flag)
         midx += 1
      if done: break
      bdate = PgUtil.adddate(edate, 0, 0, 1)

   return midx

#
# call main() to start program
#
if __name__ == "__main__": main()
