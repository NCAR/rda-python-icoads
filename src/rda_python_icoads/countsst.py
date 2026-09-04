#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countsst
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CountSst
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
from .pg_imma import PgIMMA

class CountSst(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
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
   def main(self):

      option = None
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
            continue
         ms = re.match(r'-([go])$', arg)
         if ms:
            option = ms.group(1)
            continue
         if re.match(r'^-', arg): self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            if option == 'g':
               self.PVALS['group'] = arg
            elif option == 'o':
               self.PVALS['oname'] = arg
            option = ''
         elif not self.PVALS['bdate']:
            self.PVALS['bdate'] = arg
         elif not self.PVALS['edate']:
            self.PVALS['edate'] = arg
         else:
            self.pglog(arg + ": Invalid parameter", self.LGWNEX)

      self.ivaddb_dbname()

      if not (self.PVALS['bdate'] and self.PVALS['edate'] and re.match(r'^(daily|monthly|yearly)$', self.PVALS['group'])):
         pgrec = self.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', self.LGEREX)
         print("Usage: countsst -g GroupBy (daily|monthly|yearly) BeginDate EndDate")
         print("   Group by Daily, Monthly or Yearly is mandatory")
         print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("countsst {}".format(' '.join(argv)))

      if not self.PVALS['oname']:
         self.PVALS['oname'] = "SST_COUNTS_{}_{}-{}.txt".format(self.PVALS['group'].upper(), self.PVALS['bdate'], self.PVALS['edate'])

      IMMA = open(self.PVALS['oname'], 'w')
      IMMA.write(self.PVALS['group'] + ", NOCN, ENH, SST, TOTAL\n")
      self.count_sst(IMMA)
      IMMA.close()
      self.cmdlog()
      sys.exit(0)

   #
   # count the SST values daily/monthly/yearly
   #
   def count_sst(self, fd):

      pcnt = self.init_periods()
      tcnts = [0]*4
      getdaily = 1 if self.PVALS['group'] == 'daily' else 0

      for pidx in range(pcnt):
         if getdaily:
            acnts = self.count_daily_sst(self.PVALS['bpdate'][pidx])
         else:
            acnts = self.count_period_sst(pidx)

         line = self.PVALS['period'][pidx]
         for i in range(4):
            line += ", {}".format(acnts[i])
            tcnts[i] += acnts[i]
         fd.write(line + "\n")

      if pcnt > 1:
         line = "Total"
         for i in range(4):
            line += ", {}".format(tcnts[i])
         fd.write(line + "\n")
         self.pglog("{} total for {} {} periods".format(tcnts[3], pcnt, self.PVALS['group']), self.LOGWRN)

   #
   # read icoads record from given file name and save them into RDADB
   #
   def count_period_sst(self, pidx):

      bdate = self.PVALS['bpdate'][pidx]
      edate = self.PVALS['epdate'][pidx]
      btidx = self.date2tidx(bdate)
      etidx = self.date2tidx(edate)
      tblcnt = etidx-btidx+1
      acounts = [0]*4
      acnds = ['']*tblcnt
      mcnds = ['']*tblcnt

      self.pglog("Counting SST for {} from IVADDB".format(self.PVALS['period'][pidx]), self.WARNLG)

      if tblcnt == 1:
         acnds[0] = "date BETWEEN '{}' AND '{}'".format(bdate, edate)
         mcnds[0] = "time BETWEEN '{} 00:00:00' AND '{} 23:59:59'".format(bdate, edate)
      else:
         acnds[0] = "date >= '{}'".format(bdate)
         mcnds[0] = "time >= '{} 00:00:00'".format(bdate)
         acnds[tblcnt-1] = "date <= '{}'".format(edate)
         mcnds[tblcnt-1] = "time <= '{} 23:59:59'".format(edate)

      for i in range(tblcnt): self.count_table_sst(btidx+i, acounts, acnds[i], mcnds[i])
      if acounts[3]: self.pglog("{} for {}".format(acounts[3], self.PVALS['period'][pidx]), self.LOGWRN)

      return acounts

   #
   # count IMMA records for given date
   #
   def count_daily_sst(self, cdate):

      tidx = self.date2tidx(cdate)
      acounts = [0]*4

      self.pglog("Counting SST for {} from IVADDB".format(cdate), self.WARNLG)
      acnd = "date = '{}'".format(cdate)
      mcnd = "time BETWEEN '{} 00:00:00' AND '{} 23:59:59'".format(cdate, cdate)
      self.count_table_sst(tidx, acounts, acnd, mcnd)
      if acounts[3]: self.pglog("{} for {}".format(acounts[3], cdate), self.LOGWRN)

      return acounts

   #
   # count IMMA records from one table
   #
   def count_table_sst(self, tidx, acounts, acnd, mcnd):

      table = "icoreloc_{}".format(tidx)
      cnt = self.pgget(table, "", acnd, self.LGEREX)
      if not cnt: return acounts
      acounts[3] += cnt

      table = 'domsdb.idoms_{}'.format(tidx)
      if mcnd: mcnd += ' AND '
      mcnd += "sea_water_temperature IS NOT NULL"
      acounts[2] += self.pgget(table, "", mcnd, self.LGEREX)
      acnd = mcnd + " AND sea_water_temperature_quality = 0"
      acounts[1] += self.pgget(table, "", acnd, self.LGEREX)
      acnd = mcnd + " AND sea_water_temperature_depth > 0"
      acounts[0] += self.pgget(table, "", acnd, self.LGEREX)

      return acounts

   #
   # initialize period list
   #
   def init_periods(self):

      bdate = self.PVALS['bdate']   
      if self.PVALS['group'] == "yearly":
         dfmt = "YYYY"
         eflg = "Y"
      elif self.PVALS['group'] == 'monthly':
         dfmt = "YYYY-MM"
         eflg = "M"
      else:  # must be daily
         dfmt = "YYYY-MM-DD"
         eflg = ""
      pcnt = 0
      while True:
         pcnt += 1
         self.PVALS['bpdate'].append(bdate)
         self.PVALS['period'].append(self.format_date(bdate, dfmt))
         edate = self.enddate(bdate, 0, eflg) if eflg else bdate
         if self.diffdate(self.PVALS['edate'], edate) > 0:
            self.PVALS['epdate'].append(edate)
            bdate = self.adddate(edate, 0, 0, 1)
         else:
            self.PVALS['epdate'].append(self.PVALS['edate'])
            break

      return pcnt

# main function to execute this script
def main():
   CountSst().main()

# call main() to start program
if __name__ == "__main__": main()
