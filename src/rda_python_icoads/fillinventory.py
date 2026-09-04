#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillinventory
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class FillInventory
#   Purpose : process ICOADS data files in IMMA format and fill inventory
#             information into IVADDB
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class FillInventory(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'files' : [],
         'oflag' : 0
      }

   #
   # main function to run dsarch
   #
   def main(self):

      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-s":
            self.PVALS['oflag'] |= 2
         elif arg == "-o":
            self.PVALS['oflag'] |= 1
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         else:
            self.PVALS['files'].append(arg)

      if self.PVALS['oflag'] == 3: self.pglog("Use option -o or -s, but not both", self.LGEREX)

      if not (self.PVALS['files'] or self.PVALS['oflag'] == 2):
         print("Usage: fillinventory [-(o|s)] FileNameList")
         print("   Option -o: Count daily records only if present")
         print("   Option -s: set daily counted records with table indices if present")
         print("   At least one file name needs to be present to fill inventory data")
         sys.exit(0)

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.ivaddb_dbname()
      self.cmdlog("fillinventory {}".format(' '.join(argv)))

      if self.PVALS['oflag'] == 2:
         self.refill_imma_inventory();  
      else:
         self.fill_imma_inventory()

      self.cmdlog()
      sys.exit(0)

   #
   # fill imma inventory tables
   #
   def fill_imma_inventory(self):

      fcnt = len(self.PVALS['files'])
      inventory = self.get_inventory_record(0, self.PVALS['oflag'])

      fidx = 0
      for file in self.PVALS['files']:
         inventory = self.process_imma_file(file, inventory)

      self.pglog("inventory records recorded for {} files".format(fcnt), self.LOGWRN)

   #
   # refill imma  inventory tablers
   #
   def refill_imma_inventory(self):

      dcnt = 0
      inventory = self.get_inventory_record(0, self.PVALS['oflag'])

      cdate = self.get_inventory_next_date(inventory['date'])
      while cdate:
         inventory = self.add_inventory_record('', cdate, 0, inventory, self.PVALS['oflag'])
         dcnt += 1
         cdate = self.get_inventory_next_date(inventory['date'])

      self.pglog("inventory records refilled up for {} days".format(dcnt), self.LOGWRN)

   #
   # get inventory next date for given date
   #
   def get_inventory_next_date(self, cdate):

      pgrec = self.pgget("cntldb.inventory", "min(date) mdate", ("date > '{}'".format(cdate) if cdate else ''), self.LGEREX)

      return (pgrec['mdate'] if pgrec else None)

   #
   # read icoads record from given file name and save them into IVADDB
   #
   def process_imma_file(self, fname, inventory):

      self.pglog("Record IMMA Inventory for File '{}' into IVADDB".format(fname), self.WARNLG)

      IMMA = open(fname, 'r')
      line = IMMA.readline()
      cdate = self.get_imma_date(line)
      if self.PVALS['oflag'] == 0 and cdate <= inventory['date']:
          self.pglog("{}({}): Must be later than saved {}".format(cdate, fname, inventory['date']), self.LGEREX)

      mcnt = icnt = 0
      count = 1
      while line:
         idate = self.get_imma_date(line)
         if idate != cdate:
            inventory = self.add_inventory_record(fname, cdate, count, inventory, self.PVALS['oflag'])
            mcnt += count
            count = 0
            cdate = idate
            icnt += 1

         count += 1
         line = IMMA.readline()

      IMMA.close()

      inventory = self.add_inventory_record(fname, cdate, count, inventory, self.PVALS['oflag'])
      mcnt += count
      icnt += 1
      self.pglog("{}: {} records recorded into {} inventory records".format(fname, mcnt, icnt), self.LOGWRN)

      return inventory

# main function to execute this script
def main():
   FillInventory().main()

# call main() to start program
if __name__ == "__main__": main()
