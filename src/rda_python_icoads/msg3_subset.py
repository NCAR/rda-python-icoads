#!/usr/bin/env python3
#
##################################################################################
#
#     Title : msg3_subset
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/07/2020
#             2025-02-28 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class Msg3Subset
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
from .pg_imma import PgIMMA
from rda_python_dsrqst.pg_subset import PgSubset

class Msg3Subset(PgIMMA, PgSubset):

   def __init__(self):
      super().__init__()
      self.MISSIDX = [22, 23, 24, 25]
      self.STATNUM = ['10 14 18 22 26 30 34 38 42 46 ', '11 15 19 23 27 31 35 39 43 47 ',
                 '12 16 20 24 28 32 36 40 44 48 ', '13 17 21 25 29 33 37 41 45 49']
      self.VARARRAY = {
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
      self.IDSID = 'd548001'
      self.PVALS = {
         'datadir' : self.PGLOG['DSDHOME'] + "/icoads/MSG3.0",
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
      self.PGRQST = {}
      self.INRECS = {}
      self.OUTRECS = {}

   #
   # main function to run dsarch
   #
   def main(self):

      argv = sys.argv[1:]
      self.PGLOG['LOGFILE'] = "icoads.log"

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-d":
            self.PGLOG['DBGLEVEL'] = 1000
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Unknown Option", self.LGEREX)
         elif re.match(r'^(\d+)$', arg):
            if self.PVALS['ridx']: self.pglog("{}: Request Index ({}) given already".format(arg, self.PVALS['ridx']), self.LGEREX)
            self.PVALS['ridx'] = int(arg)
         else:
            if self.PVALS['rdir']: self.pglog("{}: Request Directory ({}) given already".format(arg, self.PVALS['rdir']), self.LGEREX)
            self.PVALS['rdir'] = arg

      self.cmdlog("msg3_subset {}".format(' '.join(argv)))
      self.PGRQST = self.valid_subset_request(self.PVALS['ridx'], self.PVALS['rdir'], self.IDSID, self.LGWNEX)
      if not self.PVALS['rdir']: self.PVALS['rdir'] = self.join_paths(self.PGLOG['RQSTHOME'], self.PGRQST['rqstid'])
      self.process_subset_request()
      self.cmdlog()
      sys.exit(0)

   #
   # process a validated subset request
   #
   def process_subset_request(self):

      if not op.isdir(self.PVALS['rdir']):
         self.make_local_directory(self.PVALS['rdir'], self.LGWNEX)
      else:
         if self.request_built(self.PVALS['ridx'], self.PVALS['rdir'], self.PVALS['msgfile'], self.PGRQST['fcount'], self.LGWNEX):
            return self.pglog("MSG Subset Request built already for Index {}".format(self.PVALS['ridx']), self.LOGWRN)
         self.clean_subset_request(self.PVALS['ridx'], self.PVALS['rdir'], None, self.LGWNEX)

      cmdfiles = self.create_cmd_file()
      self.process_data(cmdfiles)

      self.change_local_directory(self.PVALS['rdir'], self.LGWNEX)
      offset = cnt = self.PVALS['outsize'] = 0
      files = self.local_glob("*{}*".format(self.PVALS['limits']))
      for wfile in files:
         self.PVALS['outsize'] += files[wfile]['data_size']
         ms = re.search(r'(\d+)$', wfile)
         if ms:
            n = int(ms.group(1))
            if n == 1: offset = cnt
            order = offset + n
         else:
            order = cnt + 1

         if self.PGRQST['file_format']: (wfile, fmt) = self.compress_local_file(wfile, self.PGRQST['file_format'], 1)
         self.add_subset_file(self.PVALS['ridx'], wfile, None, "D", "ASCII", order, None, self.LGWNEX)
         cnt += 1

      if cnt > 0:
         wfile = self.write_readme()
         cnt += 1
         self.add_subset_file(self.PVALS['ridx'], wfile, None, "O", "TEXT", cnt, None, self.LGWNEX)
         wfile = self.PVALS['statdoc']
         cnt += 1
         self.add_subset_file(self.PVALS['ridx'], wfile, self.PVALS['docdir'] + wfile, "O", "PDF", cnt, None, self.LGWNEX)
         wfile = self.PVALS['msgfile']
         cnt += 1
         self.add_subset_file(self.PVALS['ridx'], wfile, self.PVALS['docdir'] + wfile, "O", "TEXT", cnt, None, self.LGWNEX)
         if self.PVALS['insize'] > 0 and self.PVALS['insize'] != self.PGRQST['size_input']:
            self.pgexec("UPDATE dsrqst SET size_input = {} WHERE rindex = {}".format(self.PVALS['insize'], self.PVALS['ridx']))
         self.set_dsrqst_fcount(self.PVALS['ridx'], cnt, self.PVALS['insize'], self.PVALS['outsize'])
         self.pglog("{} MSG subset files added to Request Index {}".format(cnt, self.PVALS['ridx']), self.LOGWRN)
      else:
         self.set_dsrqst_fcount(self.PVALS['ridx'], 0, self.PVALS['insize'], 0)

   #
   # process reqest and create the command file for data processing
   #
   def create_cmd_file(self):

      datafiles = []
      variables = []
      cmdfiles = {}
      ystr = yend = None
      rinfo = self.PGRQST['rinfo'] if self.PGRQST['rinfo'] else self.PGRQST['note']

      for line in rinfo.split("&"):
         ms = re.search(r'(\w+)=(.+)', line)
         if not ms: continue
         token = ms.group(1)
         pstring = ms.group(2)
         if token == "dates":  # Date Limits
            dates = pstring
            self.PVALS['limits'] = dates.replace(' ', '.')
            ms = re.search(r'(\d\d\d\d)\d\d\s(\d\d\d\d)\d\d', dates)
            if ms:
               ystr = int(ms.group(1))
               yend = int(ms.group(2))
         elif token == 'lats':
            self.PVALS['lats'] = pstring
         elif token == 'lons':
            self.PVALS['lons'] = pstring
         elif token == 'resol':
            ms = re.match(r'^(\d)DEG', pstring)
            if ms: self.PVALS['resol'] = int(ms.group(1))
         elif token == 'ptype':
            self.PVALS['ptype'] = pstring.lower()
         elif token == 'vars':  # Variable Names
            variables = pstring.split(', ')

      if not variables: self.pglog("{}: No variable specified for subset Request".format(self.PVALS['ridx']), self.LGEREX)
      if not ystr: self.pglog("{}: No Time limits specified for subset Request".format(self.PVALS['ridx']), self.LGEREX)
      if self.PVALS['resol'] == 1 and ystr < 1960: self.PVALS['resol'] = 2
      pos = self.get_latitudes(self.PVALS['lats'], self.PVALS['resol'])
      self.PVALS['lats'] = "{:7.2f} {:7.2f}".format(pos[0], pos[1])
      pos = self.get_longitudes(self.PVALS['lons'], self.PVALS['resol'])
      self.PVALS['lons'] = "{:7.2f} {:7.2f}".format(pos[0], pos[1])
      datadir = "{}/{}deg".format(self.PVALS['datadir'], self.PVALS['resol'])

      # write out command file for input of Fortran code 'subset'
      self.PVALS['insize'] = 0
      for token in variables:
         group = self.VARARRAY[token][0]
         datafiles = self.get_data_files(group, self.PVALS['ptype'], ystr, yend, datadir)
         if not datafiles: continue
         cmdfile = "{}.MSG.{}".format(self.PGRQST['rqstid'], token)
         OUT = open(cmdfile, 'w')
         pstring = "Variable name : {} , description : {}, format{}\n".format(token, self.VARARRAY[token][2], self.PVALS['format'])
         self.PVALS['varlist'] += pstring
         OUT.write(pstring)
         OUT.write(self.PVALS['title'] + "\n")
         OUT.write("{} :Group number\n".format(group))
         OUT.write("{} :nstat\n".format(self.PVALS['numstat']))
         OUT.write("{} :stat index num.\n".format(self.STATNUM[self.VARARRAY[token][1]]))
         OUT.write("{} :missing data index check\n".format(self.MISSIDX[self.VARARRAY[token][1]]))
         OUT.write(self.PVALS['format'] + "\n")
         OUT.write("{} {} {} :lat-lon SW corn. and time limits\n".format(self.PVALS['lats'], self.PVALS['lons'], dates))
         OUT.write("{} :data resolution (1 or 2)\n".format(self.PVALS['resol']))
         OUT.write("{} :data type (std or enh)\n".format(self.PVALS['ptype']))
         OUT.write(token + " :variable name\n")
         OUT.write(datadir + "/\n")   # MSG data path
         OUT.write(self.PVALS['rdir'] + "/\n")  # output data path
         OUT.write("{}\n".format(len(datafiles)))  # number of MSG data files
         for datafile in datafiles:
            info = self.check_local_file("{}/{}".format(datadir, datafile))
            if info: self.PVALS['insize'] += info['data_size']
            OUT.write(datafile + "\n")

         OUT.close()
         cmdfiles[token] = cmdfile

      return cmdfiles

   #
   # gather data files 
   #
   def get_data_files(self, group, ptype, ystr, yend, datadir):

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
   def process_data(self, cmdfiles):

      for var in cmdfiles:
         infile = cmdfiles[var]
         self.INRECS[var] = self.OUTRECS[var] = 0
         if not op.isfile(infile): continue   # no input file, skip it
         retmsg = self.pgsystem("{} < {}".format(self.PVALS['subset'], infile), self.LGWNEX, 23)
         if retmsg:
            for line in retmsg.split("\n"):
               ms = re.match(r'^\s*(IN|OUT)RECS:\s+(\d+)', line)
               if ms:
                  if ms.group(1) == 'IN':
                     self.INRECS[var] = int(ms.group(2))
                  else:
                     self.OUTRECS[var] = int(ms.group(2))
               if self.PGLOG['DBGLEVEL']: self.pgdbg(1000, line)

         self.pgsystem("rm -f " + infile)

   #
   # create a readme file specified to the request
   #
   def write_readme(self):

      user = self.get_ruser_names(self.PGRQST['email'])
      readme = self.PVALS['readme'] + self.PGRQST['rqstid'].lower()
      self.pglog("Create Readme file " + readme, self.LOGWRN)
      URM = open(readme, 'w')
      RTXT = open(self.PVALS['docdir'] + self.PVALS['readtxt'], 'r')
      line = RTXT.readline()
      while line:
         if re.match(r'^#', line):  # skip comment line
            line = RTXT.readline()
            continue
         if re.search(r'__VARLIST__', line):  # print user-selected variable list
            URM.write(self.PVALS['varlist'])
            line = RTXT.readline()
            continue

         if re.search(r'__USER__', line):
            line = line.replace('__USER__', "{}<{}>".format(user['name'], self.PGRQST['email']))
         elif re.search(r'__LATS__', line):
            line = line.replace('__LATS__', self.PVALS['lats'])
         elif re.search(r'__LONS__', line):
            line = line.replace('__LONS__', self.PVALS['lons'])
         elif re.search(r'__DATES__', line):
            line = line.replace('__DATES__', self.PVALS['limits'])
         elif re.search(r'__RESOL__', line):
            line = line.replace('__RESOL__', str(self.PVALS['resol']))
         elif re.search(r'__PTYPE__', line):
            line = line.replace('__PTYPE__', self.PVALS['ptype'])
         elif re.search(r'__INRECS__', line):
            line = line.replace('__INRECS__', self.get_recs_string(self.INRECS))
         elif re.search(r'__OUTRECS__', line):
            line = line.replace('__OUTRECS__', self.get_recs_string(self.OUTRECS))
         elif re.search(r'__INSIZES__', line):
            line = line.replace('__INSIZES__', "{:.3f} MB".format(self.PVALS['insize']/1000000.))
         elif re.search(r'__OUTSIZES__', line):
            line = line.replace('__OUTSIZES__', "{:.3f} MB".format(self.PVALS['outsize']/1000000.))
         URM.write(line)
         line = RTXT.readline()

      RTXT.close()
      URM.close()

      return readme

   #
   # get string buffer of in/out record counts
   #
   def get_recs_string(self, recs):

      str = ''
      for var in recs:
         if str: str += ", "
         str += "{}({})".format(recs[var], var)

      return str

# main function to execute this script
def main():
   Msg3Subset().main()

# call main() to start program
if __name__ == "__main__": main()
