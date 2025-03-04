#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countsst
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : read ICOADS data from IVADDB and count SST records by dail, monthly
#             or yearly
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
   'bpdate' : [],
   'epdate' : [],
   'period' : [],
   'group' : None,
   'oname' : None
}

#
# main function to run dsarch
#
def main():

   option = None
   argv = sys.argv[1:]

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
         continue
      ms = re.match(r'-([go])$', arg)
      if ms:
         option = ms.group(1)
         continue
      if re.match(r'^-', arg): PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         if option == 'g':
            PVALS['group'] = arg
         elif option == 'o':
            PVALS['oname'] = arg
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
      print("Usage: countsst -g GroupBy (daily|monthly|yearly) BeginDate EndDate")
      print("   Group by Daily, Monthly or Yearly is mandatory")
      print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)
   
   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("countsst {}".format(' '.join(argv)))

   if not PVALS['oname']:
      PVALS['oname'] = "SST_COUNTS_{}_{}-{}.txt".format(PVALS['group'].upper(), PVALS['bdate'], PVALS['edate'])

   IMMA = open(PVALS['oname'], 'w')
   IMMA.write(PVALS['group'] + ", NOCN, ENH, SST, TOTAL\n")
   count_sst(IMMA)
   IMMA.close()
   PgLOG.cmdlog()
   sys.exit(0)

#
# count the SST values daily/monthly/yearly
#
def count_sst(fd):

   pcnt = init_periods()
   tcnts = [0]*4
   getdaily = 1 if PVALS['group'] == 'daily' else 0

   for pidx in range(pcnt):
      if getdaily:
         acnts = count_daily_sst(PVALS['bpdate'][pidx])
      else:
         acnts = count_period_sst(pidx)

      line = PVALS['period'][pidx]
      for i in range(4):
         line += ", {}".format(acnts[i])
         tcnts[i] += acnts[i]
      fd.write(line + "\n")

   if pcnt > 1:
      line = "Total"
      for i in range(4):
         line += ", {}".format(tcnts[i])
      fd.write(line + "\n")
      PgLOG.pglog("{} total for {} {} periods".format(tcnts[3], pcnt, PVALS['group']), PgLOG.LOGWRN)

#
# read icoads record from given file name and save them into RDADB
#
def count_period_sst(pidx):

   bdate = PVALS['bpdate'][pidx]
   edate = PVALS['epdate'][pidx]
   btidx = PgIMMA.date2tidx(bdate)
   etidx = PgIMMA.date2tidx(edate)
   tblcnt = etidx-btidx+1
   acounts = [0]*4
   acnds = ['']*tblcnt
   mcnds = ['']*tblcnt

   PgLOG.pglog("Counting SST for {} from IVADDB".format(PVALS['period'][pidx]), PgLOG.WARNLG)

   if tblcnt == 1:
      acnds[0] = "date BETWEEN '{}' AND '{}'".format(bdate, edate)
      mcnds[0] = "time BETWEEN '{} 00:00:00' AND '{} 23:59:59'".format(bdate, edate)
   else:
      acnds[0] = "date >= '{}'".format(bdate)
      mcnds[0] = "time >= '{} 00:00:00'".format(bdate)
      acnds[tblcnt-1] = "date <= '{}'".format(edate)
      mcnds[tblcnt-1] = "time <= '{} 23:59:59'".format(edate)

   for i in range(tblcnt): count_table_sst(btidx+i, acounts, acnds[i], mcnds[i])
   if acounts[3]: PgLOG.pglog("{} for {}".format(acounts[3], PVALS['period'][pidx]), PgLOG.LOGWRN)

   return acounts

#
# count IMMA records for given date
#
def count_daily_sst(cdate):

   tidx = PgIMMA.date2tidx(cdate)
   acounts = [0]*4
 
   PgLOG.pglog("Counting SST for {} from IVADDB".format(cdate), PgLOG.WARNLG)
   acnd = "date = '{}'".format(cdate)
   mcnd = "time BETWEEN '{} 00:00:00' AND '{} 23:59:59'".format(cdate, cdate)
   count_table_sst(tidx, acounts, acnd, mcnd)
   if acounts[3]: PgLOG.pglog("{} for {}".format(acounts[3], cdate), PgLOG.LOGWRN)

   return acounts

#
# count IMMA records from one table
#
def count_table_sst(tidx, acounts, acnd, mcnd):

   table = "icoreloc_{}".format(tidx)
   cnt = PgDBI.pgget(table, "", acnd, PgLOG.LGEREX)
   if not cnt: return acounts
   acounts[3] += cnt

   table = 'domsdb.idoms_{}'.format(tidx)
   if mcnd: mcnd += ' AND '
   mcnd += "sea_water_temperature IS NOT NULL"
   acounts[2] += PgDBI.pgget(table, "", mcnd, PgLOG.LGEREX)
   acnd = mcnd + " AND sea_water_temperature_quality = 0"
   acounts[1] += PgDBI.pgget(table, "", acnd, PgLOG.LGEREX)
   acnd = mcnd + " AND sea_water_temperature_depth > 0"
   acounts[0] += PgDBI.pgget(table, "", acnd, PgLOG.LGEREX)

   return acounts

#
# initialize period list
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
