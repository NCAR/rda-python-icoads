#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countattm
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : process ICOADS data files in IMMA format and count the matching, 
#             unmatching and empty records
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from rda_python_common import PgLOG
from rda_python_common import PgDBI
from . import PgIMMA

PVALS = {
   'group' : None,
   'files' : [],
   'aname' : None,
   'bym' : None,
   'eym' : None
}

ACOUNTS = {}

#
# main function
#
def main():

   option = ''
   argv = sys.argv[1:]

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == '-g':
         option = 'g'
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Invalid Option", PgLOG.LGWNEX)
      elif option:
         PVALS['group'] = arg
         option = ''
      else:
         PVALS['files'].append(arg)
   
   if not (PVALS['files'] and re.match(r'^(monthly|yearly)$', PVALS['group'])):
      print("Usage: countattm -g GroupBy (monthly|yearly) FileNameList")
      print("   Group by Monthly or Yearly is mandatory")
      print("   At least one file name needs to be present to count icoads attm data")
      sys.exit(0)

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   PgDBI.ivaddb_dbname()
   PgLOG.cmdlog("countattm {}".format(' '.join(argv)))
   for file in PVALS['files']: count_attm_file(file)
   dump_attm_counts()
   PgLOG.cmdlog()
   sys.exit(0)

#
# read icoads record from given file name and count the records
#
def count_attm_file(fname):

   PgLOG.pglog("Count attm records in File '{}'".format(fname), PgLOG.WARNLG)
   
   # Get file month
   ms = re.search(r'(\d\d\d\d)-(\d\d)', fname)
   if ms:
      yr = ms.group(1)
      mn = ms.group(2)
      ym = "{}-{}".format(yr, mn)
      if not PVALS['bym']: PVALS['bym'] = ym
      PVALS['eym'] = ym
      key = yr if PVALS['group'] == "yearly"  else ym
      if key not in ACOUNTS:
         ACOUNTS[key] = {'match' : 0, 'unmatch' : 0, 'empty' : 0, 'total' : 0}
   else:
      PgLOG.pglog(fname + ": miss year/month values in file name", PgLOG.LGEREX)

   ATTM = open(fname, 'r')
   acnt = 0
   line = ATTM.readline()
   # check and record standalone attm name
   if not PVALS['aname']: PVALS['aname'] = PgIMMA.identify_attm_name(line)
   while line:
      ACOUNTS[key]['total'] += 1
      # commet out these two line for normal records
      line = line.rstrip()
      if len(line) < 20:
         ACOUNTS[key]['empty'] += 1
      else:
         idate = PgIMMA.get_imma_date(line)
         if idate or idate is None:
            ACOUNTS[key]['match'] += 1
         else:
            ACOUNTS[key]['unmatch'] += 1
      line = ATTM.readline()
   ATTM.close()

#
# dump attm counts by group
#
def dump_attm_counts():
   
   fname = "{}_COUNTS_{}_{}-{}.txt".format(PVALS['aname'], PVALS['group'].upper(), PVALS['bym'], PVALS['eym'])
   ATTM = open(fname, 'w')
   ATTM.write(PVALS['group'] + ", match, unmatch, empty, total\n")
   
   for key in sorted(ACOUNTS):
      ATTM.write("{}, {}, {}, {}, {}\n".format(key, ACOUNTS[key]['match'],
                 ACOUNTS[key]['unmatch'], ACOUNTS[key]['empty'], ACOUNTS[key]['total']))

#
# call main() to start program
#
if __name__ == "__main__": main()
