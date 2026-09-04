#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class FillIcoads
#   Purpose : process ICOADS data files in IMMA format and fill into IVADDB
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class FillIcoads(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'uatti' : '',
         'names' : None,
         'files' : [],
         'dates' : [],
         'dtlen' : 0
      }

   #
   # main function to run dsarch
   #
   def main(self):

      addinventory = leaduid = chkexist = 0
      rn3 = -1
      argv = sys.argv[1:]

      option = None   
      for arg in argv:
         if re.match(r'-\w', arg):
            option = None
            if arg[1] == "b":
               self.PGLOG['BCKGRND'] = 1
            elif arg[1] == "a":
               self.PVALS['uatti'] = "98"
            elif arg[1] == "u":
               leaduid = 1
            elif arg[1] == "e":
               chkexist = 1
            elif arg[1] == "i":
               addinventory = 1
            elif arg[1] in "fpr":
               option = arg[1]
            else:
               self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option == 'f':
            self.get_imma_filelist(arg)
            option = None
         elif option == 'p':
            self.PVALS['dates'].append(self.format_date(arg))
            self.PVALS['dtlen'] += 1
            if self.PVALS['dtlen'] == 2: option = None
         elif option == 'r':
            rn3 = int(arg)
            option = None
         else:
            self.PVALS['files'].append(arg)

      if not self.PVALS['files']:
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

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.set_scname(dbname = 'ivaddb', scname = self.IVADSC, lnname = 'ivaddb', dbhost = self.PGLOG['PMISCHOST'])

      self.cmdlog("fillicoads {}".format(' '.join(argv)))
      self.init_current_indices(leaduid, chkexist, rn3)
      self.PVALS['names'] = '/'.join(self.IMMA_NAMES)
      self.fill_imma_data(addinventory)
      self.cmdlog()
      self.pgexit()

   #
   # read in imma file list from a given file name
   #
   def get_imma_filelist(self, fname):

      with open(fname, "r") as f:
         for line in f.readlines():
            self.PVALS['files'].append(line.strip())

   #
   # fill up imma data
   #
   def fill_imma_data(self, addinventory):

      fcnt = 0
      tcounts = [0]*self.TABLECOUNT
      for file in self.PVALS['files']:
         fcnt += 1
         acnts = self.process_imma_file(file, addinventory)
         for i in range(self.TABLECOUNT): tcounts[i] += acnts[i]

      if fcnt > 1: self.pglog("{} ({}) filled for {} files".format('/'.join(map(str, tcounts)), self.PVALS['names'], fcnt), self.LOGWRN)

   #
   # read icoads record from given file name and save them into IVADDB
   #
   def process_imma_file(self, fname, addinventory):

      iname = fname if addinventory else None
      self.pglog("Record IMMA records in File '{}' into IVADDB".format(fname), self.WARNLG)

      IMMA = open(fname, 'r', encoding = 'latin_1')
      acounts = [0]*self.TABLECOUNT
      records = {}

      # get the first valid date and do initialization
      line = IMMA.readline()
      self.identify_attm_name(line)  # check and record standalone attm name
      while line:
         idate = cdate = self.get_imma_date(line)
         if cdate and (self.PVALS['dtlen'] == 0 or self.diffdate(cdate, self.PVALS['dates'][0]) >= 0):
            self.init_indices_for_date(cdate, iname)
            records = self.get_imma_records(cdate, line, records)
            break
         line = IMMA.readline()

      line = IMMA.readline()
      while line:
         if self.PVALS['uatti'] and line[0:2] == self.PVALS['uatti']:
             records = self.get_imma_multiple_records(cdate, line, records)
         else:
            idate = self.get_imma_date(line)
            if idate:
               if idate != cdate:
                  acnts = self.add_imma_records(cdate, records)
                  for i in range(self.TABLECOUNT): acounts[i] += acnts[i]
                  records = {}
                  cdate = idate
                  if self.PVALS['dtlen'] == 2 and self.diffdate(cdate, self.PVALS['dates'][1]) > 0: break
                  self.init_indices_for_date(cdate, iname)
               records = self.get_imma_records(idate, line, records)
         line = IMMA.readline()

      IMMA.close()

      if cdate and records:
         acnts = self.add_imma_records(cdate, records)
         for i in range(self.TABLECOUNT): acounts[i] += acnts[i]

      self.pglog("{} ({}) filled from {}".format(' '.join(map(str, acounts)), self.PVALS['names'], op.basename(fname)), self.LOGWRN)

      return acounts

# main function to execute this script
def main():
   FillIcoads().main()

# call main() to start program
if __name__ == "__main__": main()
