#!/usr/bin/env python3
#
##################################################################################
#
#     Title : maxsst
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class MaxSst
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
from .pg_imma import PgIMMA

class MaxSst(PgIMMA):

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
      self.LFLDS = 'yr, mo, dy, hr, lat, lon, id'
      self.RFLDS = 'r.iidx, r.uid, sst, it, si'
      self.IFLDS = 'dck, sid, pt'
      self.TFLDS = ['yr', 'mo', 'dy', 'hr', 'lat', 'lon', 'id','sst', 'it', 'si', 'dck', 'sid', 'pt', 'uid']
      self.TITLE = ','.join(self.TFLDS)
      self.MAXSST = 400

   #
   # main function
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

      if not (self.PVALS['bdate'] and self.PVALS['edate'] and re.match(r'^(daily|monthly|yearly|all)$', self.PVALS['group'])):
         pgrec = self.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', self.LGEREX)
         print("Usage: maxsst -g GroupBy (daily|monthly|yearly|all) BeginDate EndDate")
         print("   Group by Daily, Monthly, Yearly or All is mandatory")
         print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.cmdlog("maxsst {}".format(' '.join(argv)))

      if not self.PVALS['oname']:
         self.PVALS['oname'] = "SST_MAXIMUMS_{}_{}-{}.csv".format(self.PVALS['group'].upper(), self.PVALS['bdate'], self.PVALS['edate'])

      IMMA = open(self.PVALS['oname'], 'w')
      IMMA.write("period, {}\n".format(', '.join(self.TFLDS)))
      self.maximum_sst(IMMA)
      IMMA.close()
      self.cmdlog()
      sys.exit(0)

   #
   # maximum the SST values daily/monthly/yearly
   #
   def maximum_sst(self, fd):

      pmax = self.init_periods()
      getdaily = 1 if self.PVALS['group'] == 'daily' else 0

      for pidx in range(pmax):
         if getdaily:
            maxrec = self.maximum_daily_sst(self.PVALS['bpdate'][pidx])
         else:
            maxrec = self.maximum_period_sst(pidx)
         if not maxrec: continue
         mcnt = len(maxrec['iidx'])
         for i in range(mcnt):
            line = self.PVALS['period'][pidx]
            for fld in self.TFLDS:
               line += ", {}".format(maxrec[fld][i])
            fd.write(line + "\n")

   #
   # read icoads record from given file name and save them into RDADB
   #
   def maximum_period_sst(self, pidx):

      bdate = self.PVALS['bpdate'][pidx]
      edate = self.PVALS['epdate'][pidx]
      btidx = self.date2tidx(bdate, False)
      etidx = self.date2tidx(edate, True)
      tblmax = etidx-btidx+1

      maxrec = {}
      cnds = ['']*tblmax
      itable = 'cntldb.inventory'
      bcnd = "tidx = {} AND date >= '{}'"
      ecnd = "tidx = {} AND date <= '{}'"
      brec = self.pgget(itable, 'min(miniidx) iidx', bcnd.format(btidx, bdate))
      erec = self.pgget(itable, 'max(maxiidx) iidx', ecnd.format(etidx, edate))

      self.pglog("Find MAXIMUM SST for {} from IVADDB".format(self.PVALS['period'][pidx]), self.WARNLG)

      if tblmax == 1:
         if brec and erec['iidx'] >= brec['iidx']:
           icnd = "iidx BETWEEN {} AND {}".format(brec['iidx'], erec['iidx'])
           self.maximum_table_sst(btidx, maxrec, icnd)
      else:
         for i in range(tblmax):
            if i == 0:
               if brec:
                  icnd = "iidx >= {}".format(brec['iidx'])
                  self.maximum_table_sst(btidx+i, maxrec, icnd)
            elif i == tblmax-1:
               if erec:
                  icnd = "iidx >= {}".format(erec['iidx'])
                  self.maximum_table_sst(etidx, maxrec, icnd)
            else:
               self.maximum_table_sst(btidx + i, maxrec, '')

      if maxrec:
          mcnt = len(maxrec['iidx'])
          s = 's' if mcnt > 1 else ''
          self.pglog("MAX SST {}: {} record{} for {}".format(maxrec['sst'][0], mcnt, s, self.PVALS['period'][pidx]), self.LOGWRN)

      return maxrec

   #
   # maximum IMMA records for given date
   #
   def maximum_daily_sst(self, cdate):

      tidx = self.date2tidx(cdate)
      maxrec = {}
      itable = 'cntldb.inventory'
      self.pglog("Find MAXIMUM SST for {} from IVADDB".format(cdate), self.WARNLG)
      bcnd = "tidx = {} AND date >= '{}'"
      ecnd = "tidx = {} AND date <= '{}'"
      brec = self.pgget(itable, 'min(miniidx) iidx', ecnd.format(tidx, cdate))
      erec = self.pgget(itable, 'max(maxiidx) iidx', ecnd.format(tidx, cdate))
      if brec and erec['iidx'] >= brec['iidx']:
         icnd = "iidx BETWEEN {} AND {}".format(brec['iidx'], erec['iidx'])
         self.maximum_table_sst(tidx, maxrec, icnd)
         if maxrec:
             mcnt = len(maxrec['iidx'])
             s = 's' if mcnt > 1 else ''
             self.pglog("MAX SST {}: {} record{} for {}".format(maxrec['sst'][0], mcnt, s, cdate), self.LOGWRN)

      return maxrec

   #
   # maximum IMMA records from one table
   #
   def maximum_table_sst(self, tidx, maxrec, cnd):

      rtable = "icorereg_{}".format(tidx)
      ltable = "icoreloc_{}".format(tidx)
      itable = "iicoads_{}".format(tidx)
      jtables = "{} r, {} i".format(rtable, itable)
      if cnd: cnd = 'r.{} AND '.format(cnd)
      jcnd = cnd + "r.iidx = i.iidx AND pt = 13 AND "
   #   mcnd = jcnd + "sst < {} AND si >= 0 AND it >= 0".format(MAXSST)
      mcnd = jcnd + "sst < {}".format(self.MAXSST)
      if maxrec: mcnd += " AND sst > {}".format(maxrec['sst'][0])
      srec = self.pgget(jtables, 'max(sst) sst', mcnd, self.LGEREX)
      if srec['sst'] is None: return

   #   mcnd = jcnd + "sst = {} AND si >= 0 AND it >= 0".format(srec['sst'])
      mcnd = jcnd + "sst = {}".format(srec['sst'])
      srec = self.pgmget(jtables, self.RFLDS, mcnd, self.LGEREX)
      for fld in srec: maxrec[fld] = srec[fld]

      mcnt = len(srec['iidx'])
      if mcnt == 1:
         mcnd = 'iidx = {}'.format(srec['iidx'][0])
      else:
         mcnd = 'iidx IN ({})'.format(','.join(map(str, srec['iidx'])))

      srec = self.pgmget(ltable, self.LFLDS, mcnd, self.LGEREX)
      for fld in srec: maxrec[fld] = srec[fld]

      srec = self.pgmget(itable, self.IFLDS, mcnd, self.LGEREX)
      for fld in srec: maxrec[fld] = srec[fld]

   #
   # initialize period list
   #
   def init_periods(self):

      bdate = self.PVALS['bdate']   
      if self.PVALS['group'] == "all":
         self.PVALS['bpdate'].append(bdate)
         self.PVALS['period'].append('ALL')
         self.PVALS['epdate'].append(self.PVALS['edate'])
         return 1
      elif self.PVALS['group'] == "yearly":
         dfmt = "YYYY"
         eflg = "Y"
      elif self.PVALS['group'] == 'monthly':
         dfmt = "YYYY-MM"
         eflg = "M"
      else:  # must be daily
         dfmt = "YYYY-MM-DD"
         eflg = ""
      pmax = 0
      while True:
         pmax += 1
         self.PVALS['bpdate'].append(bdate)
         self.PVALS['period'].append(self.format_date(bdate, dfmt))
         edate = self.enddate(bdate, 0, eflg) if eflg else bdate
         if self.diffdate(self.PVALS['edate'], edate) > 0:
            self.PVALS['epdate'].append(edate)
            bdate = self.adddate(edate, 0, 0, 1)
         else:
            self.PVALS['epdate'].append(self.PVALS['edate'])
            break

      return pmax

# main function to execute this script
def main():
   MaxSst().main()

# call main() to start program
if __name__ == "__main__": main()
