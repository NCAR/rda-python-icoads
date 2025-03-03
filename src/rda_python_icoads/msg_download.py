#!/usr/bin/env python3
#
##################################################################################
#
#     Title : msg_download
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 03/02/2021
#             2025-03-03 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : download MSG monthly update tar file and untar it for dsupdt
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import re
from os import path as op
from rda_python_common import PgLOG
from rda_python_common import PgUtil
from rda_python_common import PgFile

LFILES = [
   "MSG1_R3.0.2_ENH_",
   "MSG1_R3.0.2_STD_",
   "MSG1_R3.0.2_ENH_EQ_",
   "MSG1_R3.0.2_STD_EQ_",
   "MSG2_R3.0.2_ENH_",
   "MSG2_R3.0.2_STD_",
]
MFILES = [
   ["MSG1_", ".?.ENH.gz"],
   ["MSG1_", ".?.STD.gz"],
   ["MSG1_", ".?.ENH.S.gz"],
   ["MSG1_", ".?.STD.S.gz"],
   ["MSG2_", ".?.ENH.gz"],
   ["MSG2_", ".?.STD.gz"],
]
LCNT = 6

OPTIONS = {
   'CD' : None,
   'ED' : None,
   'NL' : 0,
   'NS' : 0,
   'MU' : 0
}

WEBURL = "https://www.ncei.noaa.gov/data/international-comprehensive-ocean-atmosphere/v3/archive/msg/"
SUBDIR = PgLOG.PGLOG['DSDHOME'] + "/icoads/MSG3.0"
#WPATH = "data/msg3.0.0"
#WPATH = "data/netcdf3.0.2"
WPATH = "data/netcdf3.0.2new"
PPATH = "../.."
WORKDIR = PgLOG.get_environment("ICOADSDIR", PgLOG.PGLOG['UPDTWKP'] + "/zji/icoads") + "/icoads_rt"
#SFMT = "ICOADS_v3.0.0_MSG-binary_d{}{}_c"
SFMT = "icoads-nrt_r3.0.2_msg-binary_d{}{}_c"

#
# main function to excecute this script
#
def main():

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   argv = sys.argv[1:]
   options = '|'.join(OPTIONS)
   option = None

   for arg in argv:
      if arg ==  "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
         option = None
         continue
      ms = re.match(r'^-({})$'.format(options), arg, re.I)
      if ms:
         option = ms.group(1).upper()
         if re.match(r'^(NS|NL|MU)$', option):
            OPTIONS[option] = 1
            option = None
         continue
      elif re.match(r'^-.*', arg):
         PgLOG.pglog(arg + ": Unknown Option", PgLOG.LGEREX)
      elif option:
            OPTIONS[option] = arg
            option = None
      elif not OPTIONS['ED']:
         OPTIONS['ED'] = arg
      else:
         PgLOG.pglog(arg + ": Value passed in without leading option", PgLOG.LGEREX)

   if not OPTIONS['ED']:
      print("Usage: msg_download [-MU] [-NL] [-NS] [-CD CurrentDate] [-ED] EndDate")
      print("   Provide end date for monthly MSG data to download it from $WEBURL")
      print("   Option -MU - download/build files for multiple month")
      print("   Option -NL - do not build local files")
      print("   Option -NS - do not save subset files")
      print("   Option -CD - optional current date, default to today")
      print("   Option -ED - mandatory for the end data date")
      sys.exit(0)

   PgLOG.cmdlog("msg_download {}".format(' '.join(argv)))
   PgFile.change_local_directory(WORKDIR)
   
   if not OPTIONS['CD']: OPTIONS['CD'] = PgUtil.curdate()
   
   diff = PgUtil.diffdate(OPTIONS['ED'], OPTIONS['CD'])
   if diff > 0: PgLOG.pglog("{}: data date is later than current date {}".format(OPTIONS['ED'], OPTIONS['CD']), PgLOG.LGEREX)
   
   while diff < 0:
      process_msg_files()
      if not OPTIONS['MU']: break
      OPTIONS['ED'] = PgUtil.adddate(OPTIONS['ED'], 0, 1, 0)
      diff = PgUtil.diffdate(OPTIONS['ED'], OPTIONS['CD'])
   
   PgLOG.cmdlog()
   sys.exit(0)
   
#
# process download and build MSG files for a month
#
def process_msg_files():

   ms = re.match(r'^(\d+)-(\d+)', OPTIONS['ED'])
   if ms:
      yr = ms.group(1)
      mn = ms.group(2)
      if len(mn) == 1: mn = '{:02}'.format(int(mn))
   else:
      PgLOG.pglog(OPTIONS['ED'] + ": invalid date format", PgLOG.LGEREX)

   sfile = SFMT.format(yr, mn)
   cnt = 0
   lfiles = [None]*LCNT
   lexists = [0]*LCNT
   for i in range(LCNT):
      lfiles[i] = "{}{}-{}.tar".format(LFILES[i], yr, mn)
      if PgFile.local_file_size(lfiles[i], 3) > 0:
         lexists[i] = 1
         cnt += 1

   if cnt == LCNT:
      PgLOG.pglog("{}-{}:: all {} local files created already for the month".format(yr, mn, cnt), PgLOG.LOGWRN)
      return cnt
 
   rfile = download_msg_file(sfile)
   if not rfile: return PgLOG.pglog(sfile + ": remote file NOT exists", PgLOG.LOGWRN)

   # untar downloaded remote file
#   PgLOG.pgsystem("tar -xvf {} -C {}".format(rfile, WPATH), PgLOG.LOGWRN, 5)
   PgLOG.pgsystem("tar -xvf " + rfile, PgLOG.LOGWRN, 5)

   PgFile.change_local_directory(WPATH)
   if not OPTIONS['NL']: build_msg_files(yr, mn, lfiles, lexists)
   if not OPTIONS['NS']: build_subset_files(yr, mn)
   PgLOG.pgsystem("rm -f MSG?_{}.{}*".format(yr, mn), PgLOG.LOGWRN, 1029)
   PgFile.change_local_directory(PPATH)

#
# download a MSG tar file from remote web server
#
def download_msg_file(sfile):

   rfile = sfile + ".tar"
   cmd = "pgwget -ul {} -rn {} -ex tar -fn {} -cr".format(WEBURL, sfile, rfile)
   PgLOG.pgsystem(cmd, PgLOG.LOGWRN, 5)
   if PgFile.check_local_file(rfile): return rfile

   return None

#
# build up the local MSG files for archive 
#
def build_msg_files(yr, mn, lfiles, lexists):
   
   for i in range(LCNT):
      if lexists[i]: continue
      lfile = "{}/{}".format(PPATH, lfiles[i])
      mfiles = "{}{}.{}{}".format(MFILES[i][0], yr, mn, MFILES[i][1])
      PgLOG.pgsystem("tar -cvf {} {}".format(lfile, mfiles), PgLOG.LOGWRN, 1029)

#
# build up the subset MSG files
#
def build_subset_files(yr, mn):

   grps = [3,4,5,6,7,9]
   omonth = False if mn == '01' else True
   for grp in grps:
      PgLOG.pgsystem("gunzip MSG?_{}.{}.{}.???.gz".format(yr, mn, grp), PgLOG.LOGWRN, 1029)
      build_one_subset_file("MSG1_{}.{}.{}.ENH".format(yr, mn, grp), 'enh', grp, 1, yr, omonth)
      build_one_subset_file("MSG1_{}.{}.{}.STD".format(yr, mn, grp), 'std', grp, 1, yr, omonth)
      build_one_subset_file("MSG2_{}.{}.{}.ENH".format(yr, mn, grp), 'enh', grp, 2, yr, omonth)
      build_one_subset_file("MSG2_{}.{}.{}.STD".format(yr, mn, grp), 'std', grp, 2, yr, omonth)

#
# build one subset MSG file
#
def build_one_subset_file(nfile, type, grp, deg, yr, omonth):

   # check and get the existing tar file
   lfile = "{}g{}.{}".format(type, grp, yr)
   tfile = "{}/{}deg/{}".format(SUBDIR, deg, lfile)

   if omonth and not op.isfile(lfile) and op.isfile(tfile): PgLOG.pgsystem("cp -f {} {}".format(tfile, lfile), PgLOG.LGWNEX)
   PgLOG.pgsystem("cat {} >> {}".format(nfile, lfile), PgLOG.LGWNEX)
   PgLOG.pgsystem("cp -f {} {}".format(lfile, tfile), PgLOG.LGWNEX)

#
# call main() to start program
#
if __name__ == "__main__": main()
