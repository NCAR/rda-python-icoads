#!/usr/bin/env python3
#
##################################################################################
#
#     Title : fixiidx
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 06/23/2023
#             2025-03-04 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : read ICOADS data from IVADDB and fix the iidx values in ireanqc and iivad
#             attms
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
from rda_python_common import PgLOG
from rda_python_common import PgDBI

IIDX = {}

def main():

   argv = sys.argv[1:]
   if argv and argv[0] == "-b": PgLOG.PGLOG['BCKGRND'] = 1
   PgDBI.ivaddb_dbname()
   fixiidx('iivad', 8, 24)
   fixiidx('ireanqc', 1, 25)


def fixiidx(aname, t1, t2):

   global IIDX
   count = 100000
   while t1 <= t2:
      IIDX = {}
      tcnt = fcnt = 0
      offset = 0
      tidx = t1
      t1 += 1
      tname = "{}_{}".format(aname, tidx)
      while True:
         pgrecs = PgDBI.pgmget(tname, 'lidx, iidx, uid', 'OFFSET {} LIMIT {}'.format(offset, count))
         if not pgrecs: break
         cnt = len(pgrecs['lidx'])
         for i in range(cnt):
            iidx = get_iidx(pgrecs['uid'][i], tidx)
            if iidx != pgrecs['iidx'][i]:
               fcnt += PgDBI.pgexec("UPDATE {} SET iidx = {} WHERE lidx = {}".format(tname, iidx, pgrecs['lidx'][i]), PgLOG.LGEREX)         
         offset += count
         tcnt += cnt
         PgLOG.pglog("{}/{} records fixed for {}.iidx".format(fcnt, tcnt, tname), PgLOG.LOGWRN)


def get_iidx(uid, tidx):

   if uid not in IIDX:
      tname = 'iuida_{}'.format(tidx)
      cnd = "uid = '{}'".format(uid)
      pgrec = PgDBI.pgget(tname, 'iidx', cnd)
      if not pgrec: PgLOG.pglog("{}: Error get iidx for {}".format(tname, cnd), PgLOG.LGEREX)
      IIDX[uid] = pgrec['iidx']

   return IIDX[uid]

#
# call main() to start program
#
if __name__ == "__main__": main()
