#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countattmvar
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
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
def main():

   option = None
   argv = sys.argv[1:]
   
   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
         continue
      ms = re.match(r'^-[afgjow])$', arg)
      if ms:
         option = ms.group(1)
         continue
      if re.match(r'^-', arg): PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         if option == 'a':
            PVALS['aname'] = arg
         elif option == 'g':
            PVALS['group'] = arg
         elif option == 'j':
            PVALS['jname'] = arg
         elif option == 'f':
            PVALS['fname'] = arg
         elif option == 'o':
            PVALS['oname'] = arg
         elif option == 'w':
            PVALS['wcnd'] = arg
         option = ''
      elif not PVALS['bdate']:
         PVALS['bdate'] = arg
      elif not PVALS['edate']:
         PVALS['edate'] = arg
      else:
         PgLOG.pglog(arg + ": Invalid parameter", PgLOG.LGWNEX)
   
   PgDBI.ivaddb_dbname()
   
   if(not (PVALS['bdate'] and PVALS['edate']) or not re.match(r'^(daily|monthly|yearly)$', PVALS['group']) or 
      not (PVALS['aname'] and PVALS['fname'] and PVALS['wcnd'])):
      pgrec = PgDBI.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', PgLOG.LGEREX)
      print("Usage: countattmvar -g GroupBy (daily|monthly|yearly) -a AttmName -f FieldName -w WhereCondition [-j JoinName] BeginDate EndDate")
      print("   Group by Daily, Monthly or Yearly is mandatory")
      print("   Set BeginDate and EndDate between '' and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)

   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate
   
   if PVALS['jname'] and (PVALS['jname'] == PVALS['aname'] or PVALS['jname'] == "icoreloc"): PVALS['jname'] = None
   
   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("countattmvar {}".format(' '.join(argv)))
   
   if not PVALS['oname']:
      PVALS['oname'] = "{}.{}_COUNTS_{}_{}-{}.txt".format(PVALS['aname'], PVALS['fname'],
                        PVALS['group'].upper(), PVALS['bdate'], PVALS['edate'])

   IMMA = open(PVALS['oname'], 'w')
   IMMA.write("{}, {}\n".format(PVALS['group'], PVALS['fname']))
   count_attm_variable(IMMA)
   IMMA.close()
   PgLOG.PgLOG.cmdlog()
   sys.exit(0)

#
# count the variable of a attm daily/month/y/yearly
#
def count_attm_variable(IMMA):

   pcnt = init_periods()
   tcnt = 0
   for pidx in range(pcnt):
      if PVALS['group'] == 'daily':
         acnt = count_daily_attm_variable(PVALS['bpdate'][pidx])
      else:
         acnt = count_period_attm_variable(pidx)
      if not acnt: continue
      IMMA.write("{}, {}\n".format(PVALS['period'][pidx], acnt))
      tcnt += acnt

   if pcnt > 1:
      IMMA.write("Total, {}\n".format(tcnt))
      PgLOG.pglog("{}.{}: {} total for {} {} periods".format(PVALS['aname'], PVALS['fname'], tcnt, pcnt, PVALS['group']), PgLOG.LOGWRN)

#
# read icoads record from given file name and save them into RDADB
#
def count_period_attm_variable(pidx):

   bdate = PVALS['bpdate'][pidx]
   edate = PVALS['epdate'][pidx]
   btidx = PgIMMA.date2tidx(bdate)
   etidx = PgIMMA.date2tidx(edate)
   tblcnt = etidx-btidx+1
   PgLOG.pglog("Counting {}.{} for {} from IVADDB".format(PVALS['aname'], PVALS['fname'], PVALS['period'][pidx]), PgLOG.WARNLG)
   
   # get acount from the first table
   acount = 0
   if tblcnt == 1:
      cnds = ["date BETWEEN '{}' AND '{}' AND ".format(bdate, edate)]
   else:
      cnds = ['']*tblcnt
      cnds[0] = "date >='{}' AND ".format(bdate)
      cnds[tblcnt-1] = "date <= '{}' AND ".format(edate)
   for i in range(tblcnt): acount += count_table_attm_variable(cnds[i], i + btidx)

   if acount > 0:
      PgLOG.pglog("{}.{}: {} for {} of {}".format(PVALS['aname'], PVALS['fname'], acount, PVALS['wcnd'], PVALS['period'][pidx]), PgLOG.LOGWRN)
   return acount

#
# count IMMA records for given date
#
def count_daily_attm_variable(cdate):

   tidx = PgIMMA.date2tidx(cdate)
   if not tidx: return 0
   PgLOG.pglog("Counting {}.{} for {} from IVADDB".format(PVALS['aname'], PVALS['fname'], cdate), PgLOG.WARNLG)
   acount = count_table_attm_variable("date = '{}' AND ".format(cdate), tidx)
   if acount > 0:
      PgLOG.pglog("{}.{}: {} for {} of ".format(PVALS['aname'], PVALS['fname'], acount, PVALS['wcnd'], cdate), PgLOG.LOGWRN)
   return acount

#
# count IMMA records from one table
#
def count_table_attm_variable(dcnd, tidx):

   if PVALS['jname']:
      jtable = "{}_{}".format(PVALS['jname'], tidx)
      if tidx not in PVALS['jtables']: PVALS['jtables'][tidx] = PgDBI.pgcheck(jtable)
      if not PVALS['jtables'][tidx]: return 0

   atable = "{}_{}".format(PVALS['aname'], tidx)
   if tidx not in PVALS['atables']: PVALS['atables'][tidx] = PgDBI.pgcheck(atable)
   if not PVALS['atables'][tidx]: return 0

   if PVALS['aname'] == 'icoreloc':
      if PVALS['jname']:
         table = "{} j, {} n".format(jtable, atable)
         jcnd = "j.iidx = n.iidx AND "
      else:
         table = atable
         jcnd = ""
   else:
      mtable = "icoreloc_{}".format(tidx)
      if PVALS['jname']:
         table = "{}m, {} j. {} n".format(mtable, jtable, atable)
         jcnd = "m.iidx = j.iidx AND m.iidx = n.iidx AND "
      else:
         table = "{} m, {} n".format(mtable, atable)
         cnd = "{} AND m.iidx = n.iidx AND "

   return PgDBI.pgget(table, "", dcnd + jcnd + PVALS['wcnd'], PgLOG.LGEREX)

#
# initialize the group periods
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
      if PgUtil.diffdate(edate, PVALS['edate']) < 0:
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
