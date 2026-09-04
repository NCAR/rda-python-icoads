#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fixiidx
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 06/23/2023
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class FixIidx
#   Purpose : read ICOADS data from IVADDB and fix the iidx values in ireanqc and iivad
#             attms
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
from rda_python_common.pg_dbi import PgDBI

class FixIidx(PgDBI):

   def __init__(self):
      super().__init__()
      self.IIDX = {}

   def main(self):

      argv = sys.argv[1:]
      if argv and argv[0] == "-b": self.PGLOG['BCKGRND'] = 1
      self.ivaddb_dbname()
      self.fixiidx('iivad', 8, 24)
      self.fixiidx('ireanqc', 1, 25)

   def fixiidx(self, aname, t1, t2):

      count = 100000
      while t1 <= t2:
         self.IIDX = {}
         tcnt = fcnt = 0
         offset = 0
         tidx = t1
         t1 += 1
         tname = "{}_{}".format(aname, tidx)
         while True:
            pgrecs = self.pgmget(tname, 'lidx, iidx, uid', 'OFFSET {} LIMIT {}'.format(offset, count))
            if not pgrecs: break
            cnt = len(pgrecs['lidx'])
            for i in range(cnt):
               iidx = self.get_iidx(pgrecs['uid'][i], tidx)
               if iidx != pgrecs['iidx'][i]:
                  fcnt += self.pgexec("UPDATE {} SET iidx = {} WHERE lidx = {}".format(tname, iidx, pgrecs['lidx'][i]), self.LGEREX)         
            offset += count
            tcnt += cnt
            self.pglog("{}/{} records fixed for {}.iidx".format(fcnt, tcnt, tname), self.LOGWRN)

   def get_iidx(self, uid, tidx):

      if uid not in self.IIDX:
         tname = 'iuida_{}'.format(tidx)
         cnd = "uid = '{}'".format(uid)
         pgrec = self.pgget(tname, 'iidx', cnd)
         if not pgrec: self.pglog("{}: Error get iidx for {}".format(tname, cnd), self.LGEREX)
         self.IIDX[uid] = pgrec['iidx']

      return self.IIDX[uid]

# main function to execute this script
def main():
   FixIidx().main()

# call main() to start program
if __name__ == "__main__": main()
