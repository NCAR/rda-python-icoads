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
from rda_python_common import PgUtil
from . import PgIMMA

PVALS = {
   'uatti' : '',
   'names' : None,
   'files' : [],
   'dates' : [],
   'dtlen' : 0
}

#
# main function to run dsarch
#
def main():

   addinventory = leaduid = chkexist = 0
   rn3 = -1
   argv = sys.argv[1:]

   option = None   
   for arg in argv:
      if re.match(r'-\w', arg):
         option = None
         if arg[1] == "b":
            PgLOG.PGLOG['BCKGRND'] = 1
         elif arg[1] == "a":
            PVALS['uatti'] = "98"
         elif arg[1] == "u":
            leaduid = 1
         elif arg[1] == "e":
            chkexist = 1
         elif arg[1] == "i":
            addinventory = 1
         elif arg[1] in "fpr":
            option = arg[1]
         else:
            PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option == 'f':
         get_imma_filelist(arg)
         option = None
      elif option == 'p':
         PVALS['dates'].append(PgUtil.format_date(arg))
         PVALS['dtlen'] += 1
         if PVALS['dtlen'] == 2: option = None
      elif option == 'r':
         rn3 = int(arg)
         option = None
      else:
         PVALS['files'].append(arg)

   if not PVALS['files']:
      print("Usage: fillicoads [-a] [-e] [-f InputFile] [-i] [-p BDate [EDate]] [-r RN3] [-u] FileList")
      print("   At least one file name needs to fill icoads data into Postgres Server")
      print("   Option -a: add all attms, including multi-line ones, such as IVAD and REANQC")
      print("   Option -f: provide a filename holding a list of IMMA1 files")
      print("   Option -i: add daily counting records into inventory table")
      print("   Option -p: provide a period for filling data")
      print("   Option -r: the Third digit of IMMA release number")
      print("   Option -u: standalone attachment records with leading 6-character UID")
      print("   Option -e: check existing record before adding attm")
      sys.exit(0)

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.set_scname(dbname = 'ivaddb', scname = PgIMMA.IVADSC, lnname = 'ivaddb', dbhost = PgLOG.PGLOG['PMISCHOST'])

   PgLOG.cmdlog("fillicoads {}".format(' '.join(argv)))
   PgIMMA.init_current_indices(leaduid, chkexist, rn3)
   PVALS['names'] = '/'.join(PgIMMA.IMMA_NAMES)
   fill_imma_data(addinventory)
   PgLOG.cmdlog()
   PgLOG.pgexit()

#
# read in imma file list from a given file name
#
def get_imma_filelist(fname):

   with open(fname, "r") as f:
      for line in f.readlines():
         PVALS['files'].append(line.strip())

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
   PgIMMA.identify_attm_name(line)  # check and record standalone attm name
   while line:
      idate = cdate = PgIMMA.get_imma_date(line)
      if cdate and (PVALS['dtlen'] == 0 or cdate >= PVALS['dates'][0]):
         PgIMMA.init_indices_for_date(cdate, iname)
         records = PgIMMA.get_imma_records(cdate, line, records)
         break
      line = IMMA.readline()

   line = IMMA.readline()
   while line:
      if PVALS['uatti'] and line[0:2] == PVALS['uatti']:
          records = PgIMMA.get_imma_multiple_records(cdate, line, records)
      else:
         idate = PgIMMA.get_imma_date(line)
         if idate:
            if idate != cdate:
               acnts = PgIMMA.add_imma_records(cdate, records)
               for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]
               records = {}
               cdate = idate
               if PVALS['dtlen'] == 2 and cdate > PVALS['dates'][1]: break
               PgIMMA.init_indices_for_date(cdate, iname)
            records = PgIMMA.get_imma_records(idate, line, records)
      line = IMMA.readline()

   IMMA.close()

   if cdate and records:
      acnts = PgIMMA.add_imma_records(cdate, records)
      for i in range(PgIMMA.TABLECOUNT): acounts[i] += acnts[i]

   PgLOG.pglog("{} ({}) filled from {}".format(' '.join(map(str, acounts)), PVALS['names'], op.basename(fname)), PgLOG.LOGWRN)
   
   return acounts

#
# call main() to start program
#
if __name__ == "__main__": main()
