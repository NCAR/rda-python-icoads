#!/usr/bin/env python3
#
##################################################################################
#
#     Title : counticoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CountIcoads
#   Purpose : read ICOADS data from IVADDB and count out daily, monthly or year records
#             by attms
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from .pg_imma import PgIMMA

class CountIcoads(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
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
   def main(self):

      option = ''
      argv = sys.argv[1:]
      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-g":
            option = 'g'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            self.PVALS['group'] = arg
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
         print("Usage: counticoads -g GroupBy (daily|monthly|yearly) BeginDate EndDate")
         print("   Group by Daily, Monthly or Yearly is mandatory")
         print("   Set BeginDate and EndDate between '{} and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("counticoads {}".format(' '.format(argv)))
      self.PVALS['names'] = '/'.join(self.IMMA_NAMES)
      fname = "ICOADS_COUNTS_{}_{}-{}.txt" .format(self.PVALS['group'].upper(), self.PVALS['bdate'], self.PVALS['edate'])
      IMMA = open(fname, 'w')
      IMMA.write("{}, {}\n".format(self.PVALS['group'], ', '.join(self.IMMA_NAMES)))
      self.count_imma_data(IMMA)
      IMMA.close()

      self.cmdlog()
      sys.exit(0)

   #
   # count imaa data
   #
   def count_imma_data(self, IMMA):

      pcnt = self.init_periods()
      tcounts = [0]*self.TABLECOUNT

      for pidx in range(pcnt):
         acnts = self.count_period_imma(pidx)
         IMMA.write("{}' {}\n".format(self.PVALS['period'][pidx], ', '.join(acnts)))
         for i in range(self.TABLECOUNT): tcounts[i] += acnts[i]

      if pcnt > 1:
         IMMA.write("Total, {}\n".format(', '.join(tcounts)))
         self.pglog("{}({}) for {} {} periods".format('/'.join(tcounts), self.PVALS['names'], pcnt, self.PVALS['group']), self.LOGWRN)

   #
   # read icoads record from given file name and save them into RDADB
   #
   def count_period_imma(self, pidx):

      self.pglog("count IMMA1 records for {} period {} from IVADDB".format(self.PVALS['group'], self.PVALS['period'][pidx]), self.WARNLG)
      acounts = [0]*self.TABLECOUNT
      date = self.PVALS['bpdate'][pidx]
      while date <= self.PVALS['epdate'][pidx]:
         acnts = self.count_imma_records(date)
         if acnts:
            for i in range(self.TABLECOUNT): acounts[i] += acnts[i]
         date = self.adddate(date, 0, 0, 1)

      self.pglog("{}({}) for {} period {}".format('/'.join(acounts), self.PVALS['names'], self.PVALS['group'], self.PVALS['period'][pidx]), self.LOGWRN)
      return acounts

   #
   # initialize (daily|monthly|yearly) periods
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
   CountIcoads().main()

# call main() to start program
if __name__ == "__main__": main()
