#!/usr/bin/env python3
#
##################################################################################
#
#     Title : msg3_subset
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/07/2020
#             2025-02-28 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#   Purpose : process ICOADS 3.0 MSG subset requests under control of dsrqst
#             for mouthly summary data files 
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
from . import PgIMMA
from rda_python_common import PgUtil
from rda_python_common import PgFile
from rda_python_dsrqst import PgSubset


MISSIDX = [22, 23, 24, 25]
STATNUM = ['10 14 18 22 26 30 34 38 42 46 ', '11 15 19 23 27 31 35 39 43 47 ',
           '12 16 20 24 28 32 36 40 44 48 ', '13 17 21 25 29 33 37 41 45 49']
VARARRAY = {
#  VAR : GRP IDX DESCRIPTION
   'S' : [3, 0,  'sea surface temperature              0.01 @C'],
   'A' : [3, 1,  'air temperature                      0.01 @C'],
   'Q' : [3, 2,  'specific humidity                  0.01 g/kg'],
   'R' : [3, 3,  'relative humidity                      0.1 %'],
   'W' : [4, 0,  'scalar wind                         0.01 m/s'],
   'U' : [4, 1,  'vector wind eastward component      0.01 m/s'],
   'V' : [4, 2,  'vector wind northward component     0.01 m/s'],
   'P' : [4, 3,  'sea level pressure                  0.01 hPa'],
   'C' : [5, 0,  'total cloudiness                    0.1 okta'],
   'X' : [5, 2,  'WU   (wind stress              0.1 m**2/s**2'],
   'Y' : [5, 3,  'WV    parameters)              0.1 m**2/s**2'],
   'D' : [6, 0,  'S - A = sea-air temp. diff.          0.01 @C'],
   'E' : [6, 1,  '(S - A)W                          0.1 @C m/s'],
   'F' : [6, 2,  'QS - Q = (sat. Q at S) - Q         0.01 g/kg'],
   'G' : [6, 3,  'FW = (QS - Q)W = (evap. param.) 0.1 g/kg m/s'],
   'I' : [7, 0,  'UA   (sensible-heat--transport    0.1 @C m/s'],
   'J' : [7, 1,  'VA    parameters)                 0.1 @C m/s'],
   'K' : [7, 2,  'UQ   (latent-heat--transport    0.1 g/kg m/s'],
   'L' : [7, 3,  'VQ    parameters)               0.1 g/kg m/s'],
   'M' : [9, 0,  'FU                              0.1 g/kg m/s'],
   'N' : [9, 1,  'FV                              0.1 g/kg m/s'],
   'B1' : [8, 2,  'B = W**3 (high-resolution)     0.5 m**3/s**3'],
   'B2' : [9, 3,  'B = W**3 (low-resolution)      5   m**3/s**3']
}

IDSID = 'd548001'
PVALS = {
   'datadir' : PgLOG.PGLOG['DSDHOME'] + "/icoads/MSG3.0",
   'docdir' : op.dirname(op.abspath(__file__)) + '/',
   'readtxt' : "msg3.0_subset_readme.txt",
   'readme' : "readme_msg3.0.",
   'msgfile' : 'msg',
   'statdoc' : 'R3.0-stat_doc.pdf',
   'subset'  : 'msgsubset',
   'numstat' : 10,
   'format' : "(i5,2i4,2f7.1,i5,10f8.2)",
   'title' : " YEAR MON BSZ    BLO    BLA PID2      S1      S3      S5       M       N       S       D      HT       X       Y",
   'varlist' : "",
   'ptype' : "enh",
   'resol' : 2,
   'keys' : [],
   'lats' : [],
   'lons' : [],
   'limits' : [],
   'insize' : 0,
   'outsize' : 0,
   'ridx' : 0,
   'rdir' : None
}

PGRQST = {}
INRECS = {}
OUTRECS = {}

#
# main function to run dsarch
#
def main():

   global PGRQST
   argv = sys.argv[1:]
   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   
   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-d":
         PgLOG.PGLOG['DBGLEVEL'] = 1000
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Unknown Option", PgLOG.LGEREX)
      elif re.match(r'^(\d+)$', arg):
         if PVALS['ridx']: PgLOG.pglog("{}: Request Index ({}) given already".format(arg, PVALS['ridx']), PgLOG.LGEREX)
         PVALS['ridx'] = int(arg)
      else:
         if PVALS['rdir']: PgLOG.pglog("{}: Request Directory ({}) given already".format(arg, PVALS['rdir']), PgLOG.LGEREX)
         PVALS['rdir'] = arg

   PgLOG.cmdlog("msg3_subset {}".format(' '.join(argv)))
   PGRQST = PgSubset.valid_subset_request(PVALS['ridx'], PVALS['rdir'], IDSID, PgLOG.LGWNEX)
   if not PVALS['rdir']: PVALS['rdir'] = PgLOG.join_paths(PgLOG.PGLOG['RQSTHOME'], PGRQST['rqstid'])
   process_subset_request()
   PgLOG.cmdlog()
   sys.exit(0)

#
# process a validated subset request
#
def process_subset_request():

   if not op.isdir(PVALS['rdir']):
      PgFile.make_local_directory(PVALS['rdir'], PgLOG.LGWNEX)
   else:
      if PgSubset.request_built(PVALS['ridx'], PVALS['rdir'], PVALS['msgfile'], PGRQST['fcount'], PgLOG.LGWNEX):
         return PgLOG.pglog("MSG Subset Request built already for Index {}".format(PVALS['ridx']), PgLOG.LOGWRN)
      PgSubset.clean_subset_request(PVALS['ridx'], PVALS['rdir'], None, PgLOG.LGWNEX)

   cmdfiles = create_cmd_file()
   process_data(cmdfiles)

   PgFile.change_local_directory(PVALS['rdir'], PgLOG.LGWNEX)
   offset = cnt = PVALS['outsize'] = 0
   files = PgFile.local_glob("*{}*".format(PVALS['limits']))
   for wfile in files:
      PVALS['outsize'] += files[wfile]['data_size']
      ms = re.search(r'(\d+)$', wfile)
      if ms:
         n = int(ms.group(1))
         if n == 1: offset = cnt
         order = offset + n
      else:
         order = cnt + 1
      
      if PGRQST['file_format']: (wfile, fmt) = PgFile.compress_local_file(wfile, PGRQST['file_format'], 1)
      PgSubset.add_subset_file(PVALS['ridx'], wfile, None, "D", "ASCII", order, None, PgLOG.LGWNEX)
      cnt += 1

   if cnt > 0:
      wfile = write_readme()
      cnt += 1
      PgSubset.add_subset_file(PVALS['ridx'], wfile, None, "O", "TEXT", cnt, None, PgLOG.LGWNEX)
      wfile = PVALS['statdoc']
      cnt += 1
      PgSubset.add_subset_file(PVALS['ridx'], wfile, PVALS['docdir'] + wfile, "O", "PDF", cnt, None, PgLOG.LGWNEX)
      wfile = PVALS['msgfile']
      cnt += 1
      PgSubset.add_subset_file(PVALS['ridx'], wfile, PVALS['docdir'] + wfile, "O", "TEXT", cnt, None, PgLOG.LGWNEX)
      if PVALS['insize'] > 0 and PVALS['insize'] != PGRQST['size_input']:
         PgDBI.pgexec("UPDATE dsrqst SET size_input = {} WHERE rindex = {}".format(PVALS['insize'], PVALS['ridx']))
      PgSubset.set_dsrqst_fcount(PVALS['ridx'], cnt, PVALS['insize'], PVALS['outsize'])
      PgLOG.pglog("{} MSG subset files added to Request Index {}".format(cnt, PVALS['ridx']), PgLOG.LOGWRN)
   else:
      PgSubset.set_dsrqst_fcount(PVALS['ridx'], 0, PVALS['insize'], 0)

#
# process reqest and create the command file for data processing
#
def create_cmd_file():

   datafiles = []
   variables = []
   cmdfiles = {}
   ystr = yend = None
   rinfo = PGRQST['rinfo'] if PGRQST['rinfo'] else PGRQST['note']

   for line in rinfo.split("&"):
      ms = re.search(r'(\w+)=(.+)', line)
      if not ms: continue
      token = ms.group(1)
      pstring = ms.group(2)
      if token == "dates":  # Date Limits
         dates = pstring
         PVALS['limits'] = dates.replace(' ', '.')
         ms = re.search(r'(\d\d\d\d)\d\d\s(\d\d\d\d)\d\d', dates)
         if ms:
            ystr = int(ms.group(1))
            yend = int(ms.group(2))
      elif token == 'lats':
         PVALS['lats'] = pstring
      elif token == 'lons':
         PVALS['lons'] = pstring
      elif token == 'resol':
         ms = re.match(r'^(\d)DEG', pstring)
         if ms: PVALS['resol'] = int(ms.group(1))
      elif token == 'ptype':
         PVALS['ptype'] = pstring.lower()
      elif token == 'vars':  # Variable Names
         variables = pstring.split(', ')

   if not variables: PgLOG.pglog("{}: No variable specified for subset Request".format(PVALS['ridx']), PgLOG.LGEREX)
   if not ystr: PgLOG.pglog("{}: No Time limits specified for subset Request".format(PVALS['ridx']), PgLOG.LGEREX)
   if PVALS['resol'] == 1 and ystr < 1960: PVALS['resol'] = 2
   pos = PgSubset.get_latitudes(PVALS['lats'], PVALS['resol'])
   PVALS['lats'] = "{:7.2f} {:7.2f}".format(pos[0], pos[1])
   pos = PgSubset.get_longitudes(PVALS['lons'], PVALS['resol'])
   PVALS['lons'] = "{:7.2f} {:7.2f}".format(pos[0], pos[1])
   datadir = "{}/{}deg".format(PVALS['datadir'], PVALS['resol'])

   # write out command file for input of Fortran code 'subset'
   PVALS['insize'] = 0
   for token in variables:
      group = VARARRAY[token][0]
      datafiles = get_data_files(group, PVALS['ptype'], ystr, yend, datadir)
      if not datafiles: continue
      cmdfile = "{}.MSG.{}".format(PGRQST['rqstid'], token)
      OUT = open(cmdfile, 'w')
      pstring = "Variable name : {} , description : {}, format{}\n".format(token, VARARRAY[token][2], PVALS['format'])
      PVALS['varlist'] += pstring
      OUT.write(pstring)
      OUT.write(PVALS['title'] + "\n")
      OUT.write("{} :Group number\n".format(group))
      OUT.write("{} :nstat\n".format(PVALS['numstat']))
      OUT.write("{} :stat index num.\n".format(STATNUM[VARARRAY[token][1]]))
      OUT.write("{} :missing data index check\n".format(MISSIDX[VARARRAY[token][1]]))
      OUT.write(PVALS['format'] + "\n")
      OUT.write("{} {} {} :lat-lon SW corn. and time limits\n".format(PVALS['lats'], PVALS['lons'], dates))
      OUT.write("{} :data resolution (1 or 2)\n".format(PVALS['resol']))
      OUT.write("{} :data type (std or enh)\n".format(PVALS['ptype']))
      OUT.write(token + " :variable name\n")
      OUT.write(datadir + "/\n")   # MSG data path
      OUT.write(PVALS['rdir'] + "/\n")  # output data path
      OUT.write("{}\n".format(len(datafiles)))  # number of MSG data files
      for datafile in datafiles:
         info = PgFile.check_local_file("{}/{}".format(datadir, datafile))
         if info: PVALS['insize'] += info['data_size']
         OUT.write(datafile + "\n")

      OUT.close()
      cmdfiles[token] = cmdfile

   return cmdfiles

#
# gather data files 
#
def get_data_files(group, ptype, ystr, yend, datadir):

   datafiles = []

   prefix = "{}g{}".format(ptype, group)
   for yr in range(ystr, yend+1):
      datafile = prefix + ".{}".format(yr)
      if op.isfile("{}/{}".format(datadir, datafile)):
         datafiles.append(datafile)  # include existing files only

   return datafiles

#
# process data and create the sub-dataset
#
def process_data(cmdfiles):

   for var in cmdfiles:
      infile = cmdfiles[var]
      INRECS[var] = OUTRECS[var] = 0
      if not op.isfile(infile): continue   # no input file, skip it
      retmsg = PgLOG.pgsystem("{} < {}".format(PVALS['subset'], infile), PgLOG.LGWNEX, 23)
      if retmsg:
         for line in retmsg.split("\n"):
            ms = re.match(r'^\s*(IN|OUT)RECS:\s+(\d+)', line)
            if ms:
               if ms.group(1) == 'IN':
                  INRECS[var] = int(ms.group(2))
               else:
                  OUTRECS[var] = int(ms.group(2))
            if PgLOG.PGLOG['DBGLEVEL']: PgLOG.pgdbg(1000, line)

      PgLOG.pgsystem("rm -f " + infile)

#
# create a readme file specified to the request
#
def write_readme():

   user = PgDBI.get_ruser_names(PGRQST['email'])
   readme = PVALS['readme'] + PGRQST['rqstid'].lower()
   PgLOG.pglog("Create Readme file " + readme, PgLOG.LOGWRN)
   URM = open(readme, 'w')
   RTXT = open(PVALS['docdir'] + PVALS['readtxt'], 'r')
   line = RTXT.readline()
   while line:
      if re.match(r'^#', line):  # skip comment line
         line = RTXT.readline()
         continue
      if re.search(r'__VARLIST__', line):  # print user-selected variable list
         URM.write(PVALS['varlist'])
         line = RTXT.readline()
         continue

      if re.search(r'__USER__', line):
         line = line.replace('__USER__', "{}<{}>".format(user['name'], PGRQST['email']))
      elif re.search(r'__LATS__', line):
         line = line.replace('__LATS__', PVALS['lats'])
      elif re.search(r'__LONS__', line):
         line = line.replace('__LONS__', PVALS['lons'])
      elif re.search(r'__DATES__', line):
         line = line.replace('__DATES__', PVALS['limits'])
      elif re.search(r'__RESOL__', line):
         line = line.replace('__RESOL__', str(PVALS['resol']))
      elif re.search(r'__PTYPE__', line):
         line = line.replace('__PTYPE__', PVALS['ptype'])
      elif re.search(r'__INRECS__', line):
         line = line.replace('__INRECS__', get_recs_string(INRECS))
      elif re.search(r'__OUTRECS__', line):
         line = line.replace('__OUTRECS__', get_recs_string(OUTRECS))
      elif re.search(r'__INSIZES__', line):
         line = line.replace('__INSIZES__', "{:.3f} MB".format(PVALS['insize']/1000000.))
      elif re.search(r'__OUTSIZES__', line):
         line = line.replace('__OUTSIZES__', "{:.3f} MB".format(PVALS['outsize']/1000000.))
      URM.write(line)
      line = RTXT.readline()

   RTXT.close()
   URM.close()

   return readme

#
# get string buffer of in/out record counts
#
def get_recs_string(recs):

   str = ''
   for var in recs:
      if str: str += ", "
      str += "{}({})".format(recs[var], var)

   return str

#
# call main() to start program
#
if __name__ == "__main__": main()
