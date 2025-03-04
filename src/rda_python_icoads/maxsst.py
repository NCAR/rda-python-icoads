#!/usr/bin/env python3
#
##################################################################################
#
#     Title : maxsst
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : read ICOADS data from IVADDB and find maximum SST records dailly, monthly
#             or yearly, and their associated time and locations
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

LFLDS = 'yr, mo, dy, hr, lat, lon, id'
RFLDS = 'r.iidx, r.uid, sst, it, si'
IFLDS = 'dck, sid, pt'
TFLDS = ['yr', 'mo', 'dy', 'hr', 'lat', 'lon', 'id','sst', 'it', 'si', 'dck', 'sid', 'pt', 'uid']
TITLE = ','.join(TFLDS)

MAXSST = 400

#
# main function
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

   if not (PVALS['bdate'] and PVALS['edate'] and re.match(r'^(daily|monthly|yearly|all)$', PVALS['group'])):
      pgrec = PgDBI.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', PgLOG.LGEREX)
      print("Usage: maxsst -g GroupBy (daily|monthly|yearly|all) BeginDate EndDate")
      print("   Group by Daily, Monthly, Yearly or All is mandatory")
      print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
      sys.exit(0)
   
   if PgUtil.diffdate(PVALS['bdate'], PVALS['edate']) > 0:
      tmpdate = PVALS['bdate']
      PVALS['bdate'] = PVALS['edate']
      PVALS['edate'] = tmpdate

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgLOG.cmdlog("maxsst {}".format(' '.join(argv)))

   if not PVALS['oname']:
      PVALS['oname'] = "SST_MAXIMUMS_{}_{}-{}.csv".format(PVALS['group'].upper(), PVALS['bdate'], PVALS['edate'])

   IMMA = open(PVALS['oname'], 'w')
   IMMA.write("period, {}\n".format(', '.join(TFLDS)))
   maximum_sst(IMMA)
   IMMA.close()
   PgLOG.cmdlog()
   sys.exit(0)

#
# maximum the SST values daily/monthly/yearly
#
def maximum_sst(fd):

   pmax = init_periods()
   getdaily = 1 if PVALS['group'] == 'daily' else 0

   for pidx in range(pmax):
      if getdaily:
         maxrec = maximum_daily_sst(PVALS['bpdate'][pidx])
      else:
         maxrec = maximum_period_sst(pidx)
      if not maxrec: continue
      mcnt = len(maxrec['iidx'])
      for i in range(mcnt):
         line = PVALS['period'][pidx]
         for fld in TFLDS:
            line += ", {}".format(maxrec[fld][i])
         fd.write(line + "\n")

#
# read icoads record from given file name and save them into RDADB
#
def maximum_period_sst(pidx):

   bdate = PVALS['bpdate'][pidx]
   edate = PVALS['epdate'][pidx]
   btidx = PgIMMA.date2tidx(bdate, False)
   etidx = PgIMMA.date2tidx(edate, True)
   tblmax = etidx-btidx+1
   
   maxrec = {}
   cnds = ['']*tblmax
   itable = 'cntldb.inventory'
   bcnd = "tidx = {} AND date >= '{}'"
   ecnd = "tidx = {} AND date <= '{}'"
   brec = PgDBI.pgget(itable, 'min(miniidx) iidx', bcnd.format(btidx, bdate))
   erec = PgDBI.pgget(itable, 'max(maxiidx) iidx', ecnd.format(etidx, edate))

   PgLOG.pglog("Find MAXIMUM SST for {} from IVADDB".format(PVALS['period'][pidx]), PgLOG.WARNLG)

   if tblmax == 1:
      if brec and erec['iidx'] >= brec['iidx']:
        icnd = "iidx BETWEEN {} AND {}".format(brec['iidx'], erec['iidx'])
        maximum_table_sst(btidx, maxrec, icnd)
   else:
      for i in range(tblmax):
         if i == 0:
            if brec:
               icnd = "iidx >= {}".format(brec['iidx'])
               maximum_table_sst(btidx+i, maxrec, icnd)
         elif i == tblmax-1:
            if erec:
               icnd = "iidx >= {}".format(erec['iidx'])
               maximum_table_sst(etidx, maxrec, icnd)
         else:
            maximum_table_sst(btidx + i, maxrec, '')

   if maxrec:
       mcnt = len(maxrec['iidx'])
       s = 's' if mcnt > 1 else ''
       PgLOG.pglog("MAX SST {}: {} record{} for {}".format(maxrec['sst'][0], mcnt, s, PVALS['period'][pidx]), PgLOG.LOGWRN)

   return maxrec

#
# maximum IMMA records for given date
#
def maximum_daily_sst(cdate):

   tidx = PgIMMA.date2tidx(cdate)
   maxrec = {}
   itable = 'cntldb.inventory'
   PgLOG.pglog("Find MAXIMUM SST for {} from IVADDB".format(cdate), PgLOG.WARNLG)
   bcnd = "tidx = {} AND date >= '{}'"
   ecnd = "tidx = {} AND date <= '{}'"
   brec = PgDBI.pgget(itable, 'min(miniidx) iidx', ecnd.format(tidx, cdate))
   erec = PgDBI.pgget(itable, 'max(maxiidx) iidx', ecnd.format(tidx, cdate))
   if brec and erec['iidx'] >= brec['iidx']:
      icnd = "iidx BETWEEN {} AND {}".format(brec['iidx'], erec['iidx'])
      maximum_table_sst(tidx, maxrec, icnd)
      if maxrec:
          mcnt = len(maxrec['iidx'])
          s = 's' if mcnt > 1 else ''
          PgLOG.pglog("MAX SST {}: {} record{} for {}".format(maxrec['sst'][0], mcnt, s, cdate), PgLOG.LOGWRN)

   return maxrec

#
# maximum IMMA records from one table
#
def maximum_table_sst(tidx, maxrec, cnd):

   rtable = "icorereg_{}".format(tidx)
   ltable = "icoreloc_{}".format(tidx)
   itable = "iicoads_{}".format(tidx)
   jtables = "{} r, {} i".format(rtable, itable)
   if cnd: cnd = 'r.{} AND '.format(cnd)
   jcnd = cnd + "r.iidx = i.iidx AND pt = 13 AND "
#   mcnd = jcnd + "sst < {} AND si >= 0 AND it >= 0".format(MAXSST)
   mcnd = jcnd + "sst < {}".format(MAXSST)
   if maxrec: mcnd += " AND sst > {}".format(maxrec['sst'][0])
   srec = PgDBI.pgget(jtables, 'max(sst) sst', mcnd, PgLOG.LGEREX)
   if srec['sst'] is None: return

#   mcnd = jcnd + "sst = {} AND si >= 0 AND it >= 0".format(srec['sst'])
   mcnd = jcnd + "sst = {}".format(srec['sst'])
   srec = PgDBI.pgmget(jtables, RFLDS, mcnd, PgLOG.LGEREX)
   for fld in srec: maxrec[fld] = srec[fld]

   mcnt = len(srec['iidx'])
   if mcnt == 1:
      mcnd = 'iidx = {}'.format(srec['iidx'][0])
   else:
      mcnd = 'iidx IN ({})'.format(','.join(map(str, srec['iidx'])))

   srec = PgDBI.pgmget(ltable, LFLDS, mcnd, PgLOG.LGEREX)
   for fld in srec: maxrec[fld] = srec[fld]

   srec = PgDBI.pgmget(itable, IFLDS, mcnd, PgLOG.LGEREX)
   for fld in srec: maxrec[fld] = srec[fld]

#
# initialize period list
#
def init_periods():

   bdate = PVALS['bdate']   
   if PVALS['group'] == "all":
      PVALS['bpdate'].append(bdate)
      PVALS['period'].append('ALL')
      PVALS['epdate'].append(PVALS['edate'])
      return 1
   elif PVALS['group'] == "yearly":
      dfmt = "YYYY"
      eflg = "Y"
   elif PVALS['group'] == 'monthly':
      dfmt = "YYYY-MM"
      eflg = "M"
   else:  # must be daily
      dfmt = "YYYY-MM-DD"
      eflg = ""
   pmax = 0
   while True:
      pmax += 1
      PVALS['bpdate'].append(bdate)
      PVALS['period'].append(PgUtil.format_date(bdate, dfmt))
      edate = PgUtil.enddate(bdate, 0, eflg) if eflg else bdate
      if PgUtil.diffdate(PVALS['edate'], edate) > 0:
         PVALS['epdate'].append(edate)
         bdate = PgUtil.adddate(edate, 0, 0, 1)
      else:
         PVALS['epdate'].append(PVALS['edate'])
         break

   return pmax

#
# call main() to start program
#
if __name__ == "__main__": main()
