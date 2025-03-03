#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : process ICOADS data files in IMMA format and fill into IVADDB
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
from . import PgIMMA

PVALS = {
   'uatti' : '',
   'names' : None,
   'files' : []
}

#
# main function to run dsarch
#
def main():

   addinventory = leaduid = chkexist = 0
   argv = sys.argv[1:]
   
   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-a":
         PVALS['uatti'] = "98"
      elif arg == "-u":
         leaduid = 1
      elif arg == "-e":
         chkexist = 1
      elif arg == "-i":
         addinventory = 1
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      else:
         PVALS['files'].append(arg)

   if not PVALS['files']:
      print("Usage: fillicoads [-a] [-e] [-i] [-u] FileNameList")
      print("   At least one file name needs to fill icoads data into Postgres Server")
      print("   Option -a: add all attms, including multi-line ones, such as IVAD and REANQC")
      print("   Option -i: add daily counting records into inventory table")
      print("   Option -u: standalone attachment records with leading 6-character UID")
      print("   Option -e: check existing record before adding attm")
      sys.exit(0)

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
  
   PgLOG.cmdlog("fillicoads {}".format(' '.join(argv)))
   PgIMMA.init_current_indices(leaduid, chkexist)
   PVALS['names'] = '/'.join(PgIMMA.IMMA_NAMES)
   fill_imma_data(addinventory)
   PgLOG.cmdlog()
   PgLOG.pgexit()

#
# fill up imma data
#
def fill_imma_data(addinventory):

   fcnt = 0
   tcounts = [0]*PgIMMA.TABLECOUNT
   for file in PVALS['files']:
      fcnt += 1
      acnts = process_imma_file(file, addinventory)
      for i in range(PgIMMA.TABLECOUNT): tcounts[i] += acnts[i]

   if fcnt > 1: PgLOG.pglog("{} ({}) filled for {} files".format('/'.join(map(str, tcounts)), PVALS['names'], fcnt), PgLOG.LOGWRN)

#
# read icoads record from given file name and save them into IVADDB
#
def process_imma_file(fname, addinventory):

   iname = fname if addinventory else None
   PgLOG.pglog("Record IMMA records in File '{}' into IVADDB".format(fname), PgLOG.WARNLG)

   IMMA = open(fname, 'r', encoding = 'latin_1')
   acounts = [0]*PgIMMA.TABLECOUNT
   records = {}

   # get the first valid date and do initialization
   line = IMMA.readline()
   while line:
      PgIMMA.identify_attm_name(line)  # check and record standalone attm name
      idate = cdate = PgIMMA.get_imma_date(line)
      if cdate:
         PgIMMA.init_indices_for_date(cdate, iname)
         records = PgIMMA.get_imma_records(line, cdate, records)
         break
      line = IMMA.readline()

   line = IMMA.readline()
   while line:
      if PVALS['uatti'] and line[0:2] == PVALS['uatti']:
          records = PgIMMA.get_imma_multiple_records(line, records)
      else:
         idate = PgIMMA.get_imma_date(line)
         if idate:
            if idate != cdate:
               acnts = PgIMMA.add_imma_records(cdate, records)
               for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]
               records = {}
               cdate = idate
               PgIMMA.init_indices_for_date(cdate, iname)
            records = PgIMMA.get_imma_records(line, idate, records)
      line = IMMA.readline()

   IMMA.close()

   acnts = PgIMMA.add_imma_records(cdate, records)
   for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]

   PgLOG.pglog("{} ({}) filled from {}".format(' '.join(map(str, acounts)), PVALS['names'], op.basename(fname)), PgLOG.LOGWRN)
   
   return acounts

#
# call main() to start program
#
if __name__ == "__main__": main()
