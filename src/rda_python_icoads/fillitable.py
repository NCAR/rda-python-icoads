#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillitable
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : fill ICOADS tables for specified fields, such as PT, DCK, SID, and etc.
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
def main():

   option = ''
   addvar = fillit = 0
   argv = sys.argv[1:]

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
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
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      else:
         if option == 'v':
            PVALS['vars'].append(arg)
         elif option == 'i':
            if len(PVALS['tidx']) == 2:
               PgLOG.pglog(arg + ": More than 2 table indices provided for index range", PgLOG.LGEREX)
            PVALS['tidx'].append(arg)
         elif option == 'r':
            if not PVALS['bdate']:
               PVALS['bdate'] = arg
            elif not PVALS['edate']:
               PVALS['edate'] = arg
            else:
               PgLOG.pglog("{}: More than 2 dates passed in for -{}".foramt(arg, option), PgLOG.LGWNEX)
         else:
            PgLOG.pglog(arg + ": Value passed in without leading Option", PgLOG.LGWNEX)
   
   if not (PVALS['vars'] or fillit):
      print("Usage: fillitable [-i TableIndex1 [TableIndex2]] [-r BeginDate [EndDate]] [-a] [-t] [-v VariableNameList]")
      print("   Option -i: specify table index range to fill variable tables, use one table index if TableIndex2 is missed")
      print("   Option -r: provide date range to fill variable tables")
      print("   Option -a: read key and descrition pairs from file i(pt|dck|sid).txt to add/update variable tables ipt/idck/isid")
      print("   Option -v: specify variable names (pt dck sid) to fill variable tables")
      print("   Option -t: fill dssdb.itable if present")
      PgLOG.pgexit()

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
   PgLOG.cmdlog("fillitable {}".format(' '.join(argv)))
   get_table_info(fillit)
   
   if PVALS['vars']:
      if addvar: add_field_records()
      fill_field_records()

   if fillit: fill_itable_records()
   
   PgLOG.cmdlog()
   PgLOG.pgexit()

#
# get the table info array
#
def get_table_info(fillit):

   if len(PVALS['tidx']) == 2:
      cnd = "tidx BETWEEN {} AND {}".format(PVALS['tidx'][0], PVALS['tidx'][1])
   elif len(PVALS['tidx']) == 1:
      cnd = "tidx = {}".format(PVALS['tidx'][0])
   elif PVALS['edate']:
      cnd = "date BETWEEN '{}' AND '{}'".format(PVALS['bdate'], PVALS['edate'])
   elif PVALS['edate']:
      cnd = "date >= '{}'".format(PVALS['bdate'])
   else:
      cnd = ''

   flds = "tidx, min(miniidx) miniidx, max(maxiidx) maxiidx"
   if fillit: flds += ", min(date) bdate, max(date) edate"
   PVALS['tinfo'] = PgDBI.pgmget('cntldb.inventory', flds, cnd + " GROUP BY tidx", PgLOG.LGEREX);   
   PVALS['tcnt'] = len(PVALS['tinfo']['tidx']) if PVALS['tinfo'] else 0

   if not PVALS['tcnt']: PgLOG.pglog("No table index found in IVADDB for " + cnd, PgLOG.LGEREX)

#
# add fiels records into IVADDB
#
def add_field_records():

   # add field record if not exists yet  
   for var in PVALS['vars']:
      vtable = "i" + var
      file = vtable + ".txt"
      vcnt = acnt = ucnt = 0
      IVAR = open(file, 'r')
      line = IVAR.readline()
      while line:
         line = PgLOG.pgtrim(line)
         ms = re.match(r'^(\d+)\t(\w.*)$', line)
         if ms:
            stat = add_field_value(var, vtable, ms.group(1), ms.group(2))
            vcnt += 1
            if stat == 1:
               acnt += 1
            elif stat == 2:
               ucnt += 1

      IVAR.close()
      PgLOG.pglog("{}/{} of {} values added/updated into table {}".format(acnt, ucnt, vcnt, vtable), PgLOG.LOGWRN)

#
# add a single field value
#
def add_field_value(var, vtable, key, desc):

   cnd = "{} = {}".foramt(var, key)

   pgrec = PgDBI.pgget(vtable, "*", cnd)

   if pgrec:
      if desc != pgrec['note']:
         record = {'note' : desc}
         if PgDBI.pgupdt(vtable, record, cnd, PgLOG.LGEREX): return 2
   else:
      record = {var: key, 'note' : desc}
      if PgDBI.pgadd(vtable, record, PgLOG.LGEREX): return 1

   return 0

#
# file field records in to IVADDB
#
def fill_field_records():

   # count records and set max/min dates for given variable values
   for var in PVALS['vars']:
      vtable = "i" + var
      vinfo = PgIMMA.name2number(var)
      aname = vinfo[2]
      fill_field_value(var, vtable, aname)

#
# fill a signle field value
#
def fill_field_value(var, vtable, aname):

   flds = var +", min(iidx) imin, max(iidx) imax, count(iidx) icnt"
   cnd = "GROUP BY " + var

   # find min tidx/date
   records = {}
   pgvars = {}
   pgrecs = PgDBI.pgmget(vtable, "*", "", PgLOG.LGEREX)
   vcnt = len(pgrecs[var]) if pgrecs else 0
   for i in range(vcnt):
      pgrec = PgUtil.onerecord(pgrecs, i)
      pgvars[pgrec[var]] = pgrec

   for i in range(PVALS['tcnt']):
      tidx = PVALS['tinfo']['tidx'][i]
      miniidx = PVALS['tinfo']['miniidx'][i]
      maxiidx = PVALS['tinfo']['maxiidx'][i]
      atable = "{}_{}".format(aname, tidx)
      pgrecs = PgDBI.pgmget(atable, flds, "iidx BETWEEN {} AND {} AND {} IS NOT NULL GROUP BY {}".format(miniidx, maxiidx, var, var), PgLOG.LGEREX)
      cnt = len(pgrecs[var]) if pgrecs else 0
      if not cnt: continue

      PgLOG.pglog("TIDX{}: count indices for variable {}".format(tidx, var), PgLOG.LOGWRN)
      for j in range(cnt):
         pgrec = PgUtil.onerecord(pgrecs, j)
         val = pgrec[var]
         pgvar = pgvars[val] if val in pgvars else None
         if not pgvar: PgLOG.pglog("{}: Missing value of {} in {}".format(var, val, vtable), PgLOG.LGEREX)
         if val not in records: records[val] = {}
         if not pgvar['count']:
            records[val]['count'] = pgvar['count'] = pgrec['icnt']
            records[val]['miniidx'] = pgvar['miniidx'] = pgrec['imin']
            records[val]['start_date'] = pgvar['start_date'] = PgIMMA.iidx2date(pgrec['imin'])
            records[val]['maxiidx'] = pgvar['maxiidx'] = pgrec['imax']
            records[val]['end_date'] = pgvar['end_date'] = PgIMMA.iidx2date(pgrec['imax'])
         elif pgrec['imin'] > pgvar['maxiidx']:
            pgvar['count'] += pgrec['icnt']
            records[val]['count'] = pgvar['count']
            records[val]['maxiidx'] = pgvar['maxiidx'] = pgrec['imax']
            records[val]['end_date'] = pgvar['end_date'] = PgIMMA.iidx2date(pgrec['imax'])
         elif pgrec['imax'] < pgvar['miniidx']:
            pgvar['count'] += pgrec['icnt']
            records[val]['count'] = pgvar['count']
            records[val]['miniidx'] = pgvar['miniidx'] = pgrec['imin']
            records[val]['start_date'] = pgvar['start_date'] = PgIMMA.iidx2date(pgrec['imin'])
         else:
            PgLOG.pglog("{}({}): index counted already between {} and {}".format(var, val, pgrec['imin'], pgrec['imax']), PgLOG.LOGWRN)

   cnt = 0
   for val in records:
      pgrec = records[val]
      cnt += PgDBI.pgupdt(vtable, pgrec, "{} = {}".format(var, val), PgLOG.LGEREX)
   
   PgLOG.pglog("{} of {} values recounted in table '{}'".format(cnt, vcnt, vtable), PgLOG.LOGWRN)

#
# fill in the itable records in dabase dssdb
#
def fill_itable_records():

   PgDBI.dssdb_dbname()

   acnt = ucnt = 0
   for i in range(PVALS['tcnt']):
      tidx = PVALS['tinfo']['tidx'][i]
      miniidx = PVALS['tinfo']['miniidx'][i]
      maxiidx = PVALS['tinfo']['maxiidx'][i]
      bdate = PVALS['tinfo']['bdate'][i]
      edate = PVALS['tinfo']['edate'][i]
      pgrec = PgDBI.pgget('itable', "*", "tidx = {}".format(tidx), PgLOG.LGEREX)
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
         if record and PgDBI.pgupdt('itable', record, "tidx = {}".format(tidx), PgLOG.LGEREX):
            ucnt += 1
            PgLOG.pglog(msg, PgLOG.LOGWRN)
      else:
         record['tidx'] = tidx
         record['miniidx'] = miniidx
         record['bdate'] = bdate
         record['maxiidx'] = maxiidx
         record['edate'] = edate
         msg += "Add Miniidx={} & Bdate={}, Maxiidx={} & Edate={}".format(miniidx, bdate, maxiidx, edate)
         if PgDBI.pgadd('itable', record, PgLOG.LGEREX):
            acnt += 1
            PgLOG.pglog(msg, PgLOG.LOGWRN)

   s = 's' if PVALS['tcnt'] > 1 else ''
   PgLOG.pglog("{}/{} of {} dssdb.itable records Added/Updated".format(acnt, ucnt, PVALS['tcnt']), PgLOG.LOGWRN)

#
# call main() to start program
#
if __name__ == "__main__": main()
