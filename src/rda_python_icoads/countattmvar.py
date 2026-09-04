#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countattmvar
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CountAttmVar
#   Purpose : read ICOADS data from IVADDB and count out daily, monthly or year records
#             by attms/variable
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class CountAttmVar(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'bdate' : None,
         'edate' : None,
         'bpdate' : [],
         'epdate' : [],
         'period' : [],
         'group' : None,
         'aname' : None,
         'jname' : None,
         'fname' : None,
         'oname' : None,
         'wcnd' : None,
         'atables' : {},   # cache atable names processed. value 1 table exists; 0 not exsits
         'jtables' : {}    # cache jtable names processed. value 1 table exists; 0 not exsits
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
         ms = re.match(r'^-[afgjow])$', arg)
         if ms:
            option = ms.group(1)
            continue
         if re.match(r'^-', arg): self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            if option == 'a':
               self.PVALS['aname'] = arg
            elif option == 'g':
               self.PVALS['group'] = arg
            elif option == 'j':
               self.PVALS['jname'] = arg
            elif option == 'f':
               self.PVALS['fname'] = arg
            elif option == 'o':
               self.PVALS['oname'] = arg
            elif option == 'w':
               self.PVALS['wcnd'] = arg
            option = ''
         elif not self.PVALS['bdate']:
            self.PVALS['bdate'] = arg
         elif not self.PVALS['edate']:
            self.PVALS['edate'] = arg
         else:
            self.pglog(arg + ": Invalid parameter", self.LGWNEX)

      self.ivaddb_dbname()

      if(not (self.PVALS['bdate'] and self.PVALS['edate']) or not re.match(r'^(daily|monthly|yearly)$', self.PVALS['group']) or 
         not (self.PVALS['aname'] and self.PVALS['fname'] and self.PVALS['wcnd'])):
         pgrec = self.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', self.LGEREX)
         print("Usage: countattmvar -g GroupBy (daily|monthly|yearly) -a AttmName -f FieldName -w WhereCondition [-j JoinName] BeginDate EndDate")
         print("   Group by Daily, Monthly or Yearly is mandatory")
         print("   Set BeginDate and EndDate between '' and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      if self.PVALS['jname'] and (self.PVALS['jname'] == self.PVALS['aname'] or self.PVALS['jname'] == "icoreloc"): self.PVALS['jname'] = None

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("countattmvar {}".format(' '.join(argv)))

      if not self.PVALS['oname']:
         self.PVALS['oname'] = "{}.{}_COUNTS_{}_{}-{}.txt".format(self.PVALS['aname'], self.PVALS['fname'],
                           self.PVALS['group'].upper(), self.PVALS['bdate'], self.PVALS['edate'])

      IMMA = open(self.PVALS['oname'], 'w')
      IMMA.write("{}, {}\n".format(self.PVALS['group'], self.PVALS['fname']))
      self.count_attm_variable(IMMA)
      IMMA.close()
      self.cmdlog()
      sys.exit(0)

   #
   # count the variable of a attm daily/month/y/yearly
   #
   def count_attm_variable(self, IMMA):

      pcnt = self.init_periods()
      tcnt = 0
      for pidx in range(pcnt):
         if self.PVALS['group'] == 'daily':
            acnt = self.count_daily_attm_variable(self.PVALS['bpdate'][pidx])
         else:
            acnt = self.count_period_attm_variable(pidx)
         if not acnt: continue
         IMMA.write("{}, {}\n".format(self.PVALS['period'][pidx], acnt))
         tcnt += acnt

      if pcnt > 1:
         IMMA.write("Total, {}\n".format(tcnt))
         self.pglog("{}.{}: {} total for {} {} periods".format(self.PVALS['aname'], self.PVALS['fname'], tcnt, pcnt, self.PVALS['group']), self.LOGWRN)

   #
   # read icoads record from given file name and save them into RDADB
   #
   def count_period_attm_variable(self, pidx):

      bdate = self.PVALS['bpdate'][pidx]
      edate = self.PVALS['epdate'][pidx]
      btidx = self.date2tidx(bdate)
      etidx = self.date2tidx(edate)
      tblcnt = etidx-btidx+1
      self.pglog("Counting {}.{} for {} from IVADDB".format(self.PVALS['aname'], self.PVALS['fname'], self.PVALS['period'][pidx]), self.WARNLG)

      # get acount from the first table
      acount = 0
      if tblcnt == 1:
         cnds = ["date BETWEEN '{}' AND '{}' AND ".format(bdate, edate)]
      else:
         cnds = ['']*tblcnt
         cnds[0] = "date >='{}' AND ".format(bdate)
         cnds[tblcnt-1] = "date <= '{}' AND ".format(edate)
      for i in range(tblcnt): acount += self.count_table_attm_variable(cnds[i], i + btidx)

      if acount > 0:
         self.pglog("{}.{}: {} for {} of {}".format(self.PVALS['aname'], self.PVALS['fname'], acount, self.PVALS['wcnd'], self.PVALS['period'][pidx]), self.LOGWRN)
      return acount

   #
   # count IMMA records for given date
   #
   def count_daily_attm_variable(self, cdate):

      tidx = self.date2tidx(cdate)
      if not tidx: return 0
      self.pglog("Counting {}.{} for {} from IVADDB".format(self.PVALS['aname'], self.PVALS['fname'], cdate), self.WARNLG)
      acount = self.count_table_attm_variable("date = '{}' AND ".format(cdate), tidx)
      if acount > 0:
         self.pglog("{}.{}: {} for {} of ".format(self.PVALS['aname'], self.PVALS['fname'], acount, self.PVALS['wcnd'], cdate), self.LOGWRN)
      return acount

   #
   # count IMMA records from one table
   #
   def count_table_attm_variable(self, dcnd, tidx):

      if self.PVALS['jname']:
         jtable = "{}_{}".format(self.PVALS['jname'], tidx)
         if tidx not in self.PVALS['jtables']: self.PVALS['jtables'][tidx] = self.pgcheck(jtable)
         if not self.PVALS['jtables'][tidx]: return 0

      atable = "{}_{}".format(self.PVALS['aname'], tidx)
      if tidx not in self.PVALS['atables']: self.PVALS['atables'][tidx] = self.pgcheck(atable)
      if not self.PVALS['atables'][tidx]: return 0

      if self.PVALS['aname'] == 'icoreloc':
         if self.PVALS['jname']:
            table = "{} j, {} n".format(jtable, atable)
            jcnd = "j.iidx = n.iidx AND "
         else:
            table = atable
            jcnd = ""
      else:
         mtable = "icoreloc_{}".format(tidx)
         if self.PVALS['jname']:
            table = "{}m, {} j. {} n".format(mtable, jtable, atable)
            jcnd = "m.iidx = j.iidx AND m.iidx = n.iidx AND "
         else:
            table = "{} m, {} n".format(mtable, atable)
            cnd = "{} AND m.iidx = n.iidx AND "

      return self.pgget(table, "", dcnd + jcnd + self.PVALS['wcnd'], self.LGEREX)

   #
   # initialize the group periods
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
         if self.diffdate(edate, self.PVALS['edate']) < 0:
            self.PVALS['epdate'].append(edate)
            bdate = self.adddate(edate, 0, 0, 1)
         else:
            self.PVALS['epdate'].append(self.PVALS['edate'])
            break

      return pcnt

# main function to execute this script
def main():
   CountAttmVar().main()

# call main() to start program
if __name__ == "__main__": main()
