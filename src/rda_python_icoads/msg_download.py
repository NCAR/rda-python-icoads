#!/usr/bin/env python3
#
##################################################################################
#
#     Title : msg_download
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 03/02/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class MsgDownload
#   Purpose : download MSG monthly update tar file and untar it for dsupdt
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from os import path as op
from rda_python_common.pg_file import PgFile

class MsgDownload(PgFile):

   def __init__(self):
      super().__init__()
      self.LFILES = [
         "MSG1_R3.0.2_ENH_",
         "MSG1_R3.0.2_STD_",
         "MSG1_R3.0.2_ENH_EQ_",
         "MSG1_R3.0.2_STD_EQ_",
         "MSG2_R3.0.2_ENH_",
         "MSG2_R3.0.2_STD_",
      ]
      self.MFILES = [
         ["MSG1_", ".?.ENH.gz"],
         ["MSG1_", ".?.STD.gz"],
         ["MSG1_", ".?.ENH.S.gz"],
         ["MSG1_", ".?.STD.S.gz"],
         ["MSG2_", ".?.ENH.gz"],
         ["MSG2_", ".?.STD.gz"],
      ]
      self.LCNT = 6
      self.OPTIONS = {
         'CD' : None,
         'ED' : None,
         'NL' : 0,
         'NS' : 0,
         'MU' : 0
      }
      self.WEBURL = "https://www.ncei.noaa.gov/data/international-comprehensive-ocean-atmosphere/v3/archive/msg/"
      self.SUBDIR = self.PGLOG['DSDHOME'] + "/icoads/MSG3.0"
      #WPATH = "data/msg3.0.0"
      #WPATH = "data/netcdf3.0.2"
      self.WPATH = "data/netcdf3.0.2new"
      self.PPATH = "../.."
      self.WORKDIR = self.get_environment("ICOADSDIR", self.PGLOG['UPDTWKP'] + "/zji/icoads") + "/icoads_rt"
      #SFMT = "ICOADS_v3.0.0_MSG-binary_d{}{}_c"
      self.SFMT = "icoads-nrt_r3.0.2_msg-binary_d{}{}_c"

   #
   # main function to excecute this script
   #
   def main(self):

      self.PGLOG['LOGFILE'] = "icoads.log"
      argv = sys.argv[1:]
      options = '|'.join(self.OPTIONS)
      option = None

      for arg in argv:
         if arg ==  "-b":
            self.PGLOG['BCKGRND'] = 1
            option = None
            continue
         ms = re.match(r'^-({})$'.format(options), arg, re.I)
         if ms:
            option = ms.group(1).upper()
            if re.match(r'^(NS|NL|MU)$', option):
               self.OPTIONS[option] = 1
               option = None
            continue
         elif re.match(r'^-.*', arg):
            self.pglog(arg + ": Unknown Option", self.LGEREX)
         elif option:
               self.OPTIONS[option] = arg
               option = None
         elif not self.OPTIONS['ED']:
            self.OPTIONS['ED'] = arg
         else:
            self.pglog(arg + ": Value passed in without leading option", self.LGEREX)

      if not self.OPTIONS['ED']:
         print("Usage: msg_download [-MU] [-NL] [-NS] [-CD CurrentDate] [-ED] EndDate")
         print("   Provide end date for monthly MSG data to download it from $WEBURL")
         print("   Option -MU - download/build files for multiple month")
         print("   Option -NL - do not build local files")
         print("   Option -NS - do not save subset files")
         print("   Option -CD - optional current date, default to today")
         print("   Option -ED - mandatory for the end data date")
         sys.exit(0)

      self.cmdlog("msg_download {}".format(' '.join(argv)))
      self.change_local_directory(self.WORKDIR)

      if not self.OPTIONS['CD']: self.OPTIONS['CD'] = self.curdate()

      diff = self.diffdate(self.OPTIONS['ED'], self.OPTIONS['CD'])
      if diff > 0: self.pglog("{}: data date is later than current date {}".format(self.OPTIONS['ED'], self.OPTIONS['CD']), self.LGEREX)

      while diff < 0:
         self.process_msg_files()
         if not self.OPTIONS['MU']: break
         self.OPTIONS['ED'] = self.adddate(self.OPTIONS['ED'], 0, 1, 0)
         diff = self.diffdate(self.OPTIONS['ED'], self.OPTIONS['CD'])

      self.cmdlog()
      sys.exit(0)

   #
   # process download and build MSG files for a month
   #
   def process_msg_files(self):

      ms = re.match(r'^(\d+)-(\d+)', self.OPTIONS['ED'])
      if ms:
         yr = ms.group(1)
         mn = ms.group(2)
         if len(mn) == 1: mn = '{:02}'.format(int(mn))
      else:
         self.pglog(self.OPTIONS['ED'] + ": invalid date format", self.LGEREX)

      sfile = self.SFMT.format(yr, mn)
      cnt = 0
      lfiles = [None]*self.LCNT
      lexists = [0]*self.LCNT
      for i in range(self.LCNT):
         lfiles[i] = "{}{}-{}.tar".format(self.LFILES[i], yr, mn)
         if self.local_file_size(lfiles[i], 3) > 0:
            lexists[i] = 1
            cnt += 1

      if cnt == self.LCNT:
         self.pglog("{}-{}:: all {} local files created already for the month".format(yr, mn, cnt), self.LOGWRN)
         return cnt

      rfile = self.download_msg_file(sfile)
      if not rfile: return self.pglog(sfile + ": remote file NOT exists", self.LOGWRN)

      # untar downloaded remote file
   #   PgLOG.pgsystem("tar -xvf {} -C {}".format(rfile, WPATH), PgLOG.LOGWRN, 5)
      self.pgsystem("tar -xvf " + rfile, self.LOGWRN, 5)

      self.change_local_directory(self.WPATH)
      if not self.OPTIONS['NL']: self.build_msg_files(yr, mn, lfiles, lexists)
      if not self.OPTIONS['NS']: self.build_subset_files(yr, mn)
      self.pgsystem("rm -f MSG?_{}.{}*".format(yr, mn), self.LOGWRN, 1029)
      self.change_local_directory(self.PPATH)

   #
   # download a MSG tar file from remote web server
   #
   def download_msg_file(self, sfile):

      rfile = sfile + ".tar"
      cmd = "pgwget -ul {} -rn {} -ex tar -fn {} -cr".format(self.WEBURL, sfile, rfile)
      self.pgsystem(cmd, self.LOGWRN, 5)
      if self.check_local_file(rfile): return rfile

      return None

   #
   # build up the local MSG files for archive 
   #
   def build_msg_files(self, yr, mn, lfiles, lexists):

      for i in range(self.LCNT):
         if lexists[i]: continue
         lfile = "{}/{}".format(self.PPATH, lfiles[i])
         mfiles = "{}{}.{}{}".format(self.MFILES[i][0], yr, mn, self.MFILES[i][1])
         self.pgsystem("tar -cvf {} {}".format(lfile, mfiles), self.LOGWRN, 1029)

   #
   # build up the subset MSG files
   #
   def build_subset_files(self, yr, mn):

      grps = [3,4,5,6,7,9]
      omonth = False if mn == '01' else True
      for grp in grps:
         self.pgsystem("gunzip MSG?_{}.{}.{}.???.gz".format(yr, mn, grp), self.LOGWRN, 1029)
         self.build_one_subset_file("MSG1_{}.{}.{}.ENH".format(yr, mn, grp), 'enh', grp, 1, yr, omonth)
         self.build_one_subset_file("MSG1_{}.{}.{}.STD".format(yr, mn, grp), 'std', grp, 1, yr, omonth)
         self.build_one_subset_file("MSG2_{}.{}.{}.ENH".format(yr, mn, grp), 'enh', grp, 2, yr, omonth)
         self.build_one_subset_file("MSG2_{}.{}.{}.STD".format(yr, mn, grp), 'std', grp, 2, yr, omonth)

   #
   # build one subset MSG file
   #
   def build_one_subset_file(self, nfile, type, grp, deg, yr, omonth):

      # check and get the existing tar file
      lfile = "{}g{}.{}".format(type, grp, yr)
      tfile = "{}/{}deg/{}".format(self.SUBDIR, deg, lfile)

      if omonth and not op.isfile(lfile) and op.isfile(tfile): self.pgsystem("cp -f {} {}".format(tfile, lfile), self.LGWNEX)
      self.pgsystem("cat {} >> {}".format(nfile, lfile), self.LGWNEX)
      self.pgsystem("cp -f {} {}".format(lfile, tfile), self.LGWNEX)

# main function to execute this script
def main():
   MsgDownload().main()

# call main() to start program
if __name__ == "__main__": main()
