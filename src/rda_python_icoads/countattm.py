#!/usr/bin/env python3
#
##################################################################################
#
#     Title : countattm
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/09/2021
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CountAttm
#   Purpose : process ICOADS data files in IMMA format and count the matching, 
#             unmatching and empty records
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from .pg_imma import PgIMMA

class CountAttm(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'group' : None,
         'files' : [],
         'aname' : None,
         'bym' : None,
         'eym' : None
      }
      self.ACOUNTS = {}

   #
   # main function
   #
   def main(self):

      option = ''
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == '-g':
            option = 'g'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            self.PVALS['group'] = arg
            option = ''
         else:
            self.PVALS['files'].append(arg)

      if not (self.PVALS['files'] and re.match(r'^(monthly|yearly)$', self.PVALS['group'])):
         print("Usage: countattm -g GroupBy (monthly|yearly) FileNameList")
         print("   Group by Monthly or Yearly is mandatory")
         print("   At least one file name needs to be present to count icoads attm data")
         sys.exit(0)

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.ivaddb_dbname()
      self.cmdlog("countattm {}".format(' '.join(argv)))
      for file in self.PVALS['files']: self.count_attm_file(file)
      self.dump_attm_counts()
      self.cmdlog()
      sys.exit(0)

   #
   # read icoads record from given file name and count the records
   #
   def count_attm_file(self, fname):

      self.pglog("Count attm records in File '{}'".format(fname), self.WARNLG)

      # Get file month
      ms = re.search(r'(\d\d\d\d)-(\d\d)', fname)
      if ms:
         yr = ms.group(1)
         mn = ms.group(2)
         ym = "{}-{}".format(yr, mn)
         if not self.PVALS['bym']: self.PVALS['bym'] = ym
         self.PVALS['eym'] = ym
         key = yr if self.PVALS['group'] == "yearly"  else ym
         if key not in self.ACOUNTS:
            self.ACOUNTS[key] = {'match' : 0, 'unmatch' : 0, 'empty' : 0, 'total' : 0}
      else:
         self.pglog(fname + ": miss year/month values in file name", self.LGEREX)

      ATTM = open(fname, 'r')
      acnt = 0
      line = ATTM.readline()
      # check and record standalone attm name
      if not self.PVALS['aname']: self.PVALS['aname'] = self.identify_attm_name(line)
      while line:
         self.ACOUNTS[key]['total'] += 1
         # commet out these two line for normal records
         line = line.rstrip()
         if len(line) < 20:
            self.ACOUNTS[key]['empty'] += 1
         else:
            idate = self.get_imma_date(line)
            if idate or idate is None:
               self.ACOUNTS[key]['match'] += 1
            else:
               self.ACOUNTS[key]['unmatch'] += 1
         line = ATTM.readline()
      ATTM.close()

   #
   # dump attm counts by group
   #
   def dump_attm_counts(self):

      fname = "{}_COUNTS_{}_{}-{}.txt".format(self.PVALS['aname'], self.PVALS['group'].upper(), self.PVALS['bym'], self.PVALS['eym'])
      ATTM = open(fname, 'w')
      ATTM.write(self.PVALS['group'] + ", match, unmatch, empty, total\n")

      for key in sorted(self.ACOUNTS):
         ATTM.write("{}, {}, {}, {}, {}\n".format(key, self.ACOUNTS[key]['match'],
                    self.ACOUNTS[key]['unmatch'], self.ACOUNTS[key]['empty'], self.ACOUNTS[key]['total']))

# main function to execute this script
def main():
   CountAttm().main()

# call main() to start program
if __name__ == "__main__": main()
