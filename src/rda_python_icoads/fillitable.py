#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillitable
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class FillItable
#   Purpose : fill ICOADS tables for specified fields, such as PT, DCK, SID, and etc.
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class FillItable(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'vars' : [],
         'tinfo' : None,
         'tcnt' : 0,
         'tidx' : [],
         'bdate' : None,
         'edate' : None,
      }

   #
   # main function to run dsarch
   #
   def main(self):

      option = ''
      addvar = fillit = 0
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
            option = ''
         elif arg == "-a":
            addvar = 1
            option = ''
         elif arg == "-t":
            fillit = 1
            option = ''
         elif arg == "-i":
            option = 'i'
         elif arg == "-r":
            option = 'r'
         elif arg == "-v":
            option = 'v'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         else:
            if option == 'v':
               self.PVALS['vars'].append(arg)
            elif option == 'i':
               if len(self.PVALS['tidx']) == 2:
                  self.pglog(arg + ": More than 2 table indices provided for index range", self.LGEREX)
               self.PVALS['tidx'].append(arg)
            elif option == 'r':
               if not self.PVALS['bdate']:
                  self.PVALS['bdate'] = arg
               elif not self.PVALS['edate']:
                  self.PVALS['edate'] = arg
               else:
                  self.pglog("{}: More than 2 dates passed in for -{}".foramt(arg, option), self.LGWNEX)
            else:
               self.pglog(arg + ": Value passed in without leading Option", self.LGWNEX)

      if not (self.PVALS['vars'] or fillit):
         print("Usage: fillitable [-i TableIndex1 [TableIndex2]] [-r BeginDate [EndDate]] [-a] [-t] [-v VariableNameList]")
         print("   Option -i: specify table index range to fill variable tables, use one table index if TableIndex2 is missed")
         print("   Option -r: provide date range to fill variable tables")
         print("   Option -a: read key and descrition pairs from file i(pt|dck|sid).txt to add/update variable tables ipt/idck/isid")
         print("   Option -v: specify variable names (pt dck sid) to fill variable tables")
         print("   Option -t: fill dssdb.itable if present")
         self.pgexit()

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.ivaddb_dbname()
      self.cmdlog("fillitable {}".format(' '.join(argv)))
      self.get_table_info(fillit)

      if self.PVALS['vars']:
         if addvar: self.add_field_records()
         self.fill_field_records()

      if fillit: self.fill_itable_records()

      self.cmdlog()
      self.pgexit()

   #
   # get the table info array
   #
   def get_table_info(self, fillit):

      if len(self.PVALS['tidx']) == 2:
         cnd = "tidx BETWEEN {} AND {}".format(self.PVALS['tidx'][0], self.PVALS['tidx'][1])
      elif len(self.PVALS['tidx']) == 1:
         cnd = "tidx = {}".format(self.PVALS['tidx'][0])
      elif self.PVALS['edate']:
         cnd = "date BETWEEN '{}' AND '{}'".format(self.PVALS['bdate'], self.PVALS['edate'])
      elif self.PVALS['edate']:
         cnd = "date >= '{}'".format(self.PVALS['bdate'])
      else:
         cnd = ''

      flds = "tidx, min(miniidx) miniidx, max(maxiidx) maxiidx"
      if fillit: flds += ", min(date) bdate, max(date) edate"
      self.PVALS['tinfo'] = self.pgmget('cntldb.inventory', flds, cnd + " GROUP BY tidx", self.LGEREX);   
      self.PVALS['tcnt'] = len(self.PVALS['tinfo']['tidx']) if self.PVALS['tinfo'] else 0

      if not self.PVALS['tcnt']: self.pglog("No table index found in IVADDB for " + cnd, self.LGEREX)

   #
   # add fiels records into IVADDB
   #
   def add_field_records(self):

      # add field record if not exists yet  
      for var in self.PVALS['vars']:
         vtable = "i" + var
         file = vtable + ".txt"
         vcnt = acnt = ucnt = 0
         IVAR = open(file, 'r')
         line = IVAR.readline()
         while line:
            line = self.pgtrim(line)
            ms = re.match(r'^(\d+)\t(\w.*)$', line)
            if ms:
               stat = self.add_field_value(var, vtable, ms.group(1), ms.group(2))
               vcnt += 1
               if stat == 1:
                  acnt += 1
               elif stat == 2:
                  ucnt += 1
            line = IVAR.readline()

         IVAR.close()
         self.pglog("{}/{} of {} values added/updated into table {}".format(acnt, ucnt, vcnt, vtable), self.LOGWRN)

   #
   # add a single field value
   #
   def add_field_value(self, var, vtable, key, desc):

      cnd = "{} = {}".format(var, key)

      pgrec = self.pgget(vtable, "*", cnd)

      if pgrec:
         if desc != pgrec['note']:
            record = {'note' : desc}
            if self.pgupdt(vtable, record, cnd, self.LGEREX): return 2
      else:
         record = {var: key, 'note' : desc}
         if self.pgadd(vtable, record, self.LGEREX): return 1

      return 0

   #
   # file field records in to IVADDB
   #
   def fill_field_records(self):

      # count records and set max/min dates for given variable values
      for var in self.PVALS['vars']:
         vtable = "i" + var
         vinfo = self.name2number(var)
         aname = vinfo[2]
         self.fill_field_value(var, vtable, aname)

   #
   # fill a signle field value
   #
   def fill_field_value(self, var, vtable, aname):

      flds = var +", min(iidx) imin, max(iidx) imax, count(iidx) icnt"
      cnd = "GROUP BY " + var

      # find min tidx/date
      records = {}
      pgvars = {}
      pgrecs = self.pgmget(vtable, "*", "", self.LGEREX)
      vcnt = len(pgrecs[var]) if pgrecs else 0
      for i in range(vcnt):
         pgrec = self.onerecord(pgrecs, i)
         pgvars[pgrec[var]] = pgrec

      for i in range(self.PVALS['tcnt']):
         tidx = self.PVALS['tinfo']['tidx'][i]
         miniidx = self.PVALS['tinfo']['miniidx'][i]
         maxiidx = self.PVALS['tinfo']['maxiidx'][i]
         atable = "{}_{}".format(aname, tidx)
         pgrecs = self.pgmget(atable, flds, "iidx BETWEEN {} AND {} AND {} IS NOT NULL GROUP BY {}".format(miniidx, maxiidx, var, var), self.LGEREX)
         cnt = len(pgrecs[var]) if pgrecs else 0
         if not cnt: continue

         self.pglog("TIDX{}: count indices for variable {}".format(tidx, var), self.LOGWRN)
         for j in range(cnt):
            pgrec = self.onerecord(pgrecs, j)
            val = pgrec[var]
            pgvar = pgvars[val] if val in pgvars else None
            if not pgvar: self.pglog("{}: Missing value of {} in {}".format(var, val, vtable), self.LGEREX)
            if val not in records: records[val] = {}
            if not pgvar['count']:
               records[val]['count'] = pgvar['count'] = pgrec['icnt']
               records[val]['miniidx'] = pgvar['miniidx'] = pgrec['imin']
               records[val]['start_date'] = pgvar['start_date'] = self.iidx2date(pgrec['imin'])
               records[val]['maxiidx'] = pgvar['maxiidx'] = pgrec['imax']
               records[val]['end_date'] = pgvar['end_date'] = self.iidx2date(pgrec['imax'])
            elif pgrec['imin'] > pgvar['maxiidx']:
               pgvar['count'] += pgrec['icnt']
               records[val]['count'] = pgvar['count']
               records[val]['maxiidx'] = pgvar['maxiidx'] = pgrec['imax']
               records[val]['end_date'] = pgvar['end_date'] = self.iidx2date(pgrec['imax'])
            elif pgrec['imax'] < pgvar['miniidx']:
               pgvar['count'] += pgrec['icnt']
               records[val]['count'] = pgvar['count']
               records[val]['miniidx'] = pgvar['miniidx'] = pgrec['imin']
               records[val]['start_date'] = pgvar['start_date'] = self.iidx2date(pgrec['imin'])
            else:
               self.pglog("{}({}): index counted already between {} and {}".format(var, val, pgrec['imin'], pgrec['imax']), self.LOGWRN)

      cnt = 0
      for val in records:
         pgrec = records[val]
         cnt += self.pgupdt(vtable, pgrec, "{} = {}".format(var, val), self.LGEREX)

      self.pglog("{} of {} values recounted in table '{}'".format(cnt, vcnt, vtable), self.LOGWRN)

   #
   # fill in the itable records in dabase dssdb
   #
   def fill_itable_records(self):

      self.dssdb_dbname()

      acnt = ucnt = 0
      for i in range(self.PVALS['tcnt']):
         tidx = self.PVALS['tinfo']['tidx'][i]
         miniidx = self.PVALS['tinfo']['miniidx'][i]
         maxiidx = self.PVALS['tinfo']['maxiidx'][i]
         bdate = self.PVALS['tinfo']['bdate'][i]
         edate = self.PVALS['tinfo']['edate'][i]
         pgrec = self.pgget('itable', "*", "tidx = {}".format(tidx), self.LGEREX)
         record = {}
         msg = "{}: ".format(tidx)
         if pgrec:
            sep = ''
            msg += "Change "
            if miniidx < pgrec['miniidx']:
               record['miniidx'] = miniidx
               record['bdate'] = bdate
               sep = ', '
               msg += "Miniidx from {} to {} & Bdate from {} to {}".format(pgrec['miniidx'], miniidx, pgrec['bdate'], bdate)
            if maxiidx > pgrec['maxiidx']:
               record['maxiidx'] = maxiidx
               record['edate'] = edate
               msg += "{}Maxiidx from {} to {} & Edate from {} to {}".format(sep, pgrec['maxiidx'], maxiidx, pgrec['edate'], edate)
            if record and self.pgupdt('itable', record, "tidx = {}".format(tidx), self.LGEREX):
               ucnt += 1
               self.pglog(msg, self.LOGWRN)
         else:
            record['tidx'] = tidx
            record['miniidx'] = miniidx
            record['bdate'] = bdate
            record['maxiidx'] = maxiidx
            record['edate'] = edate
            msg += "Add Miniidx={} & Bdate={}, Maxiidx={} & Edate={}".format(miniidx, bdate, maxiidx, edate)
            if self.pgadd('itable', record, self.LGEREX):
               acnt += 1
               self.pglog(msg, self.LOGWRN)

      s = 's' if self.PVALS['tcnt'] > 1 else ''
      self.pglog("{}/{} of {} dssdb.itable records Added/Updated".format(acnt, ucnt, self.PVALS['tcnt']), self.LOGWRN)

# main function to execute this script
def main():
   FillItable().main()

# call main() to start program
if __name__ == "__main__": main()
