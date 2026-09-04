#!/usr/bin/env python3
#
##################################################################################
#
#     Title : checkicoads
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 12/30/2020
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class CheckIcoads
#   Purpose : check and compare ICOADS data files and IVADDB records
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
from os import path as op
from .pg_imma import PgIMMA

class CheckIcoads(PgIMMA):

   def __init__(self):
      super().__init__()
      self.PVALS = {
         'bdate' : None,
         'edate' : None,
         'bmdate' : [],
         'emdate' : [],
         'fname' : [],
         'flag' : [],   # 1 - file exists, 2 - db records exist, 3 - both
         'mproc' : 10,
         'fpattern' : "IMMA1_R3.0.0_<YYYY-MM>",
         'readall' : 0
      }

   #
   # main function to run dsarch
   #
   def main(self):

      option = ''
      argv = sys.argv[1:]

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-a":
            self.PVALS['readall'] = 1
         elif arg == "-f":
            option = 'f'
         elif arg == "-m":
            option = 'm'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Invalid Option", self.LGWNEX)
         elif option:
            if option == 'f':
               self.PVALS['fpattern'] = arg
            elif option == 'm':
               self.PVALS['mproc'] = arg
            option = ''
         elif not self.PVALS['bdate']:
            self.PVALS['bdate'] = arg
         elif not self.PVALS['edate']:
            self.PVALS['edate'] = arg
         else:
            self.pglog(arg + ": Invalid parameter", self.LGWNEX)

      self.PGLOG['LOGFILE'] = "icoads.log"
      self.ivaddb_dbname()

      if not (self.PVALS['bdate'] and self.PVALS['edate']):
         pgrec = self.pgget("cntldb.inventory", "min(date) bdate, max(date) edate", '', self.LGEREX)
         print("Usage: checkicoads [-a] [-m mproc] [-f FilePattern] BeginDate EndDate")
         print("   Default FilePattern is " + self.PVALS['fpattern'])
         print("   Option -a - read all attms, including multi-line ones, such as IVAD and REANQC")
         print("   Option -m - start up to given number of processes, one for each month (Default to 10)")
         print("   Set BeginDate and EndDate between '{}' and '{}'".format(pgrec['bdate'], pgrec['edate']))
         sys.exit(0)

      if self.diffdate(self.PVALS['bdate'], self.PVALS['edate']) > 0:
         tmpdate = self.PVALS['bdate']
         self.PVALS['bdate'] = self.PVALS['edate']
         self.PVALS['edate'] = tmpdate

      self.cmdlog("checkicoads {}".format(' '.join(argv)))
      self.check_imma_data()
      self.cmdlog()
      sys.exit(0)

   #
   # check imma data
   #
   def check_imma_data(self):

      mcnt = self.init_months()
      if mcnt == 1: self.PVALS['mproc'] = 1
      if self.PVALS['mproc'] > 1:
         self.start_none_daemon('writeicoads', '', self.PGLOG['CURUID'], self.PVALS['mproc'], 300, 1)

      for midx in range(mcnt):
         fname = self.PVALS['fname'][midx]
         if op.isfile(fname +".cnt"): continue    # monthly file counted already
         if self.PVALS['mproc'] > 1:
            stat = self.start_child("checkicoads_{}".format(midx), self.LOGWRN, 1)  # try to start a child process
            if stat <= 0:
               sys.exit(1)   # something wrong
            elif self.PGSIG['PPID'] > 1:
               self.check_imma_file(fname, midx)
               sys.exit(0)  # stop child process
            else:
               self.pgdisconnect(0)  # disconnect database for reconnection
               continue   # continue for next midx
         else:
            self.check_imma_file(fname, midx)

      if self.PVALS['mproc'] > 1: self.check_child(None, 0, self.LOGWRN, 1)

      self.dump_final_counts()

   #
   # compare icoads records from given file name and IVADDB
   #
   def check_imma_file(self, fname, midx):

      self.pglog("Count IMMA records in File '{}'".format(fname), self.WARNLG)
      flag = self.PVALS['flag'][midx]

      acnts = [0]*self.TABLECOUNT
      acounts = [0]*self.TABLECOUNT

      if flag&1:
         IMMA = open(fname, 'r')
         line = IMMA.readline()   
         while line:
            if self.PVALS['readall'] and re.match(r'^98', line):
                self.get_imma_multiple_counts(line, acnts)
            else:
               self.get_imma_counts(line, acnts)
            line.IMMA.readline()
         IMMA.close()
         for i in range(self.TABLECOUNT): acounts[i] = acnts[i]

      if flag&2:
         self.pglog("Count IMMA records in in IVADDB", self.WARNLG)
         cdate = bdate = self.PVALS['bmdate'][midx]
         edate = self.PVALS['emdate'][midx]
         while cdate <= edate:
            acnts = self.count_imma_records(cdate, 0, self.PVALS['readall'])
            cdate = self.adddate(cdate, 0, 0, 1)
            if acnts:
               for i in range(self.TABLECOUNT): acounts[i] -= acnts[i]

      self.dump_monthly_counts(fname, acounts)

   #
   # dump monthly counts
   #
   def dump_monthly_counts(self, fname, acounts):

      oname = fname + ".cnt"
      IMMA = open(oname, 'w')
      IMMA.write("{}, {}\n".format(fname, ', '.join(acounts)))
      IMMA.close()

   #
   # concat all monthly counts into one
   #
   def dump_final_counts(self):

      fname = "ICOADS_DIFF_COUNTS.csv"

      IMMA = open(fname, 'w')
      IMMA.write("FileName, {}\n".format(', '.join(self.IMMA_NAMES)))
      IMMA.close()
      self.pgsystem("cat *.cnt >> " + fname)

   #
   # initialize the month list
   #
   def init_months(self):

      seps = ["<" , ">"];  # temporal pattern delimiters
      match = "[^" + seps[1] + "]+"

      ms = re.search(r'{}({}){}'.format(seps[0], match, seps[1]), self.PVALS['fpattern'])
      if ms:
         tpattern = ms.group(1)
         treplace = "{}{}{}".format(seps[0], tpattern, seps[1])
      else:
         self.pglog(self.PVALS['fpattern'] + ": Not temporal pattern found to get month list", self.LGEREX)

      bdate = self.PVALS['bdate']
      done = midx = 0
      while True:
         edate = self.enddate(bdate, 0, 'M')
         if self.diffdate(self.PVALS['edate'], edate) <= 0:
            edate = self.PVALS['edate']
            done = 1
         mdate = self.format_date(bdate, tpattern)
         fname = self.PVALS['fpattern'].replace(treplace, mdate)
         flag = 0
         if op.isfile(fname): flag += 1
         if self.pgget("cntldb.inventory", "", "date BETWEEN '{}' AND '{}'".format(bdate, edate), self.LGEREX):
            flag += 2
         if flag:
            self.PVALS['bmdate'].append(bdate)
            self.PVALS['emdate'].append(edate)
            self.PVALS['fname'].append(fname)
            self.PVALS['flag'].append(flag)
            midx += 1
         if done: break
         bdate = self.adddate(edate, 0, 0, 1)

      return midx

# main function to execute this script
def main():
   CheckIcoads().main()

# call main() to start program
if __name__ == "__main__": main()
