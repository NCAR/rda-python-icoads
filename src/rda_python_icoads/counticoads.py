#!/usr/bin/env python3
#
##################################################################################
#
#     Title : counticoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : read ICOADS data from IVADDB and count out daily, monthly or year records
#             by attms
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from rda_python_common import PgLOG
from rda_python_common import PgDBI
from rda_python_common import PgUtil
from . import PgIMMA

PVALS = {
   'bdate' : None,
   'edate' : None,
   'bpdate' : [],
   'epdate' : [],
   'period' : [],
   'group' : None,
   'names' : None
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
      elif arg == "-g":
         option = 'g'
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         PVALS['group'] = arg
         option = ''
      elif not PVALS['bdate']:
         PVALS['bdate'] = arg
      elif not PVALS['edate']:
         PVALS['edate'] = arg
      else:
         PgLOG.pglog(arg + ": Invalid parameter", PgLOG.LGWNEX)
   
   PgDBI.ivaddb_dbname()
   if not (PVALS['bdate'] and PVALS['edate'] and re.match(r'^(daily|monthly|yearly)$', PVALS['group'])):
      pgrec = PgDBI.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', PgLOG.LGEREX)
      print("Usage: counticoads -g GroupBy (daily|monthly|yearly) BeginDate EndDate")
      print("   Group by Daily, Monthly or Yearly is mandatory")
      print("   Set BeginDate and EndDate between '{} and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)
   
   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("counticoads {}".format(' '.format(argv)))
   PVALS['names'] = '/'.join(PgIMMA.IMMA_NAMES)
   fname = "ICOADS_COUNTS_{}_{}-{}.txt" .format(PVALS['group'].upper(), PVALS['bdate'], PVALS['edate'])
   IMMA = open(fname, 'w')
   IMMA.write("{}, {}\n".format(PVALS['group'], ', '.join(PgIMMA.IMMA_NAMES)))
   count_imma_data(IMMA)
   IMMA.close()

   PgLOG.cmdlog()
   sys.exit(0)

#
# count imaa data
#
def count_imma_data(IMMA):

   pcnt = init_periods()
   tcounts = [0]*PgIMMA.TABLECOUNT

   for pidx in range(pcnt):
      acnts = count_period_imma(pidx)
      IMMA.write("{}' {}\n".format(PVALS['period'][pidx], ', '.join(acnts)))
      for i in range(PgIMMA.TABLECOUNT): tcounts[i] += acnts[i]

   if pcnt > 1:
      IMMA.write("Total, {}\n".format(', '.join(tcounts)))
      PgLOG.pglog("{}({}) for {} {} periods".format('/'.join(tcounts), PVALS['names'], pcnt, PVALS['group']), PgLOG.LOGWRN)



#
# read icoads record from given file name and save them into RDADB
#
def count_period_imma(pidx):

   PgLOG.pglog("count IMMA1 records for {} period {} from IVADDB".format(PVALS['group'], PVALS['period'][pidx]), PgLOG.WARNLG)
   acounts = [0]*PgIMMA.TABLECOUNT
   date = PVALS['bpdate'][pidx]
   while date <= PVALS['epdate'][pidx]:
      acnts = PgIMMA.count_imma_records(date)
      if acnts:
         for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]
      date = PgUtil.adddate(date, 0, 0, 1)

   PgLOG.pglog("{}({}) for {} period {}".format('/'.join(acounts), PVALS['names'], PVALS['group'], PVALS['period'][pidx]), PgLOG.LOGWRN)
   return acounts

#
# initialize (daily|monthly|yearly) periods
#
def init_periods():

   bdate = PVALS['bdate']
   if PVALS['group'] == "yearly":
      dfmt = "YYYY"
      eflg = "Y"
   elif PVALS['group'] == 'monthly':
      dfmt = "YYYY-MM"
      eflg = "M"
   else:  # must be daily
      dfmt = "YYYY-MM-DD"
      eflg = ""

   pcnt = 0
   while True:
      pcnt += 1
      PVALS['bpdate'].append(bdate)
      PVALS['period'].append(PgUtil.format_date(bdate, dfmt))
      edate = PgUtil.enddate(bdate, 0, eflg) if eflg else bdate
      if PgUtil.diffdate(PVALS['edate'], edate) > 0:
         PVALS['epdate'].append(edate)
         bdate = PgUtil.adddate(edate, 0, 0, 1)
      else:
         PVALS['epdate'].append(PVALS['edate'])
         break

   return pcnt

#
# call main() to start program
#
if __name__ == "__main__": main()
