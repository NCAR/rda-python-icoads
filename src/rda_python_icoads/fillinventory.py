#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fillinventory
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/31/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
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
from rda_python_common import PgLOG
from rda_python_common import PgDBI
from rda_python_common import PgUtil
from . import PgIMMA

PVALS = {
   'files' : [],
   'oflag' : 0
}

#
# main function to run dsarch
#
def main():

   argv = sys.argv[1:]
   
   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-s":
         PVALS['oflag'] |= 2
      elif arg == "-o":
         PVALS['oflag'] |= 1
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      else:
         PVALS['files'].append(arg)
   
   if PVALS['oflag'] == 3: PgLOG.pglog("Use option -o or -s, but not both", PgLOG.LGEREX)
   
   if not (PVALS['files'] or PVALS['oflag'] == 2):
      print("Usage: fillinventory [-(o|s)] FileNameList")
      print("   Option -o: Count daily records only if present")
      print("   Option -s: set daily counted records with table indices if present")
      print("   At least one file name needs to be present to fill inventory data")
      sys.exit(0)

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
   PgLOG.cmdlog("fillinventory {}".format(' '.join(argv)))
   
   if PVALS['oflag'] == 2:
      refill_imma_inventory();  
   else:
      fill_imma_inventory()
   
   PgLOG.cmdlog()
   sys.exit(0)

#
# fill imma inventory tables
#
def fill_imma_inventory():

   fcnt = len(PVALS['files'])
   inventory = PgIMMA.get_inventory_record(0, PVALS['oflag'])

   fidx = 0
   for file in PVALS['files']:
      inventory = process_imma_file(file, inventory)

   PgLOG.pglog("inventory records recorded for {} files".format(fcnt), PgLOG.LOGWRN)

#
# refill imma  inventory tablers
#
def refill_imma_inventory():

   dcnt = 0
   inventory = PgIMMA.get_inventory_record(0, PVALS['oflag'])

   cdate = get_inventory_next_date(inventory['date'])
   while cdate:
      inventory = PgIMMA.add_inventory_record('', cdate, 0, inventory, PVALS['oflag'])
      dcnt += 1
      cdate = get_inventory_next_date(inventory['date'])

   PgLOG.pglog("inventory records refilled up for {} days".format(dcnt), PgLOG.LOGWRN)

#
# get inventory next date for given date
#
def get_inventory_next_date(cdate):

   pgrec = PgDBI.pgget("cntldb.inventory", "min(date) mdate", ("date > '{}'".format(cdate) if cdate else ''), PgLOG.LGEREX)

   return (pgrec['mdate'] if pgrec else None)

#
# read icoads record from given file name and save them into IVADDB
#
def process_imma_file(fname, inventory):

   PgLOG.pglog("Record IMMA Inventory for File '{}' into IVADDB".format(fname), PgLOG.WARNLG)

   IMMA = open(fname, 'r')
   line = IMMA.readline()
   cdate = PgIMMA.get_imma_date(line)
   if PVALS['oflag'] == 0 and cdate <= inventory['date']:
       PgLOG.pglog("{}({}): Must be later than saved {}".format(cdate, fname, inventory['date']), PgLOG.LGEREX)

   mcnt = icnt = 0
   count = 1
   while line:
      idate = PgIMMA.get_imma_date(line)
      if idate != cdate:
         inventory = PgIMMA.add_inventory_record(fname, cdate, count, inventory, PVALS['oflag'])
         mcnt += count
         count = 0
         cdate = idate
         icnt += 1

      count += 1
      line = IMMA.readline()

   IMMA.close()

   inventory = PgIMMA.add_inventory_record(fname, cdate, count, inventory, PVALS['oflag'])
   mcnt += count
   icnt += 1
   PgLOG.pglog("{}: {} records recorded into {} inventory records".format(fname, mcnt, icnt), PgLOG.LOGWRN)

   return inventory

#
# call main() to start program
#
if __name__ == "__main__": main()
