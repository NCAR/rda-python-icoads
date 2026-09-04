#!/usr/bin/env python3
#
##################################################################################
#
#     Title : imma1_subset
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/04/2021
#            2025-02-18 transferred to package rda_python_icoads from
#            https://github.com/NCAR/rda-icoads.git
#             2026-09-04 convert to class Imma1Subset
#   Purpose : process ICOADS requests under control of dsrqst
#             for data in PostgreSQL IVADDB in IMMA1 format
#
#    Github: https://github.com/NCAR/rda-python-icoads.git
#
##################################################################################

import sys
import os
import re
import glob
from os import path as op
from .pg_imma import PgIMMA
from rda_python_dsrqst.pg_subset import PgSubset

class Imma1Subset(PgIMMA, PgSubset):

   def __init__(self):
      super().__init__()
      self.IDSID = 'd548000'
      self.VAR2DB = {'IS' : "ics"}
      self.PVALS = {
         'codedir' : op.dirname(op.abspath(__file__)) + '/',
         'rdimma1' : "rdimma1_csv.f",
         'readhtml' : "README_R3.0_Subset.html",
         'readme' : "readme_imma1.",
         'html2pdf' : "wkhtmltopdf",
         'resol' : 0.02,
         'trmcnt' : 0,    # count of trim variables selected
         'dates' : [],    # [bdate, edate]
         'lats' : [],     # [slat, nlat]
         'lons' : [],     # [wlon, elon]
         'flts' : [],
         'vars' : [],
         'fmts' : {},
         'rinfo' : {},
         'vinfo' : {},
         'tidx' : [],
         'facnt' : 0,      # full attm count, for Reanqc and Ivad attms
         'bdate' : [],
         'edate' : [],
         'fachar' : 97,    # chr(97) = 'a'
      #  hash array if specified
         'pts' : [],
         'dcks' : [],
         'sids' : [],
         'iopts' : 0,
      }
      self.FAVARS = {}  # hash of ireanqc and iivad, values are selected source name-var
      self.FSFLDS = {}  # hash of selected data variables in FACNDS
      self.FSSRCS = {}  # hash of ireanqc and iivad, values are array of selected source names
      self.FSCNDS = {}  # hash of ireanqc and iivad, values are array of conditions for variables in FSFLDS
      self.FACNDS = {
         'ERA-20C' : 'dprp = 1',
         'CERA-20C' : 'dprp = 2',
         'FS01' : "arci = 'FS01'",
         'BKT' : "arci = ' BKT'"
      }   # additional condition for full attm
      self.FAFLDS = {'d' : [0, 18], 'w' : [0, 20], 'slp' : [0, 25], 'at' : [0, 29]}
      self.FASRCS = {
         'ERA-20C' : ['d', 'w', 'slp', 'at'],
         'CERA-20C' : ['d', 'w', 'slp', 'at'],
         'FS01' : ['w'],
         'BKT' : ['at']
      }
      self.TRIMS = {'sst' : 0, 'at' : 0, 'd' : 0, 'w' : 0, 'slp' : 0, 'wbt' : 0, 'dpt' : 0, 'rh' : 0}
      # Optional attms for subset. Append var-list to Replace <OPTATTMS> in the README template file
      self.OPTATTMS = {
         'headline' : "<h2>Details for optional selections</h2>\n<ul>\n",
         'iimmt5' : "<li>P/V <i>Immt</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=37\">Table C5, page 37</a>\n<ul><li><i>\n",
         'imodqc' : "<li>P/V <i>Mod-qc</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=38\">Table C6, page 38</a>\n<ul><li><i>\n",
         'imetavos' : "<li>P/V <i>Meta-vos</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=39\">Table C7, page 39</a><ul><li><i>\n",
         'inocn' : "<li>P/V <i>Nocn</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=40\">Table C8, page 40</a><ul><li><i>\n",
         'iecr' : "<li>P/V <i>Ecr</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=41\">Table C9, page 41</a><ul><li><i>\n",
         'ireanqc' : "<li>P/V <i>Rean-qc</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=42\">Table C95, page 42</a><ul>\n",
         'iivad' : "<li>P/V <i>Ivad</i>, <a href=\"http://rda.ucar.edu/datasets/" + self.IDSID + "/docs/R3.0-imma1.pdf#page=43\">Table C96, page 43</a><ul>\n"
      }
      self.PGRQST = self.PGFILE = None
      self.pgcmd = 'imma1_subset'
      self.PSTEP = 32
      self.TSPLIT = 1

   #
   # main function to run dsarch
   #
   def main(self):


      self.PGLOG['LOGFILE'] = "icoads.log"
      argv = sys.argv[1:]
      option = rdir = None
      fidx = ridx = 0

      for arg in argv:
         if arg == "-b":
            self.PGLOG['BCKGRND'] = 1
         elif arg == "-d":
            self.PGLOG['DBGLEVEL'] = 1000
         elif arg == "-f":
            option = 'f'
         elif re.match(r'^-', arg):
            self.pglog(arg + ": Unknown Option", self.LGEREX)
         elif option and option == 'f':
            fidx = int(arg)
            option = None
         elif re.match(r'^(\d+)$', arg):
            if ridx == 0:
               ridx = int(arg)
            else:
               self.pglog("{}: Request Index ({}) given already".format(arg, ridx), self.LGEREX)
         else:
            if rdir: self.pglog("{}: Request Directory ({}) given already".format(arg, rdir), self.LGEREX)
            rdir = arg

      self.cmdlog("{} {}".format(self.pgcmd, ' '.join(argv)))
      self.dssdb_scname()
      if fidx:
         fcnd = "findex = {}".format(fidx)
         self.PGFILE = self.pgget('wfrqst', '*', fcnd, self.LGEREX)
         if not self.PGFILE: self.pglog(fcnd + ": Request File Not in RDADB", self.LGEREX)
         if ridx == 0: ridx = self.PGFILE['rindex']
      self.PGRQST = self.valid_subset_request(ridx, rdir, self.IDSID, self.LGWNEX)
      if not rdir: rdir = self.join_paths(self.PGLOG['RQSTHOME'], self.PGRQST['rqstid'])
      rstr = "{}-Rqst{}".format(self.PGRQST['dsid'], ridx)
      if fidx > 0: rstr += "-" + self.PGFILE['wfile']

      if fidx:
         self.process_subset_file(ridx, fidx, rdir, rstr)
      else:
         self.process_subset_request(ridx, rdir, rstr)

      self.cmdlog()
      sys.exit(0)

   #
   # set the table info array
   #
   def get_table_info(self, dates):

      bdate = self.validate_date(dates[0])
      edate = self.validate_date(dates[1])
      cnd = "bdate <= '{}' AND edate >= '{}'".format(edate, bdate)
      pgrecs = self.pgmget('itable', "tidx, bdate, edate", cnd + " ORDER BY tidx", self.LGEREX)
      tcnt = len(pgrecs['tidx']) if pgrecs else 0
      if not tcnt: self.pglog("No table index found in dssdb.itable for " + cnd, self.LGEREX)
      self.PVALS['tidx'] = pgrecs['tidx']
      self.PVALS['bdate'] = [bdate]
      self.PVALS['bdate'].extend([str(d) for d in pgrecs['bdate'][1:]])
      self.PVALS['edate'] = [str(d) for d in pgrecs['edate'][:-1]]
      self.PVALS['edate'].append(edate)

      return tcnt

   #
   # get the float format string
   #
   def get_float_format(self, resl):

      prec = 0
      while resl < 1:
         prec += 1
         resl *=10

      return r'{:.%df}' % prec if prec else ''

   #
   # set variable information
   #
   def set_var_info(self):

      vars = self.PVALS['vars']
      flts = self.PVALS['flts']
      anames = []
      tcodes = []
      avars = {}
      ovars = {}
      uvars = {}
      dvars = {}
      alens = {}
      aprecs = {}
      fmts = {}
      maxs = {}
      fscnts = {}

      vcnt = len(vars)
      pname = ''
      for i in range(vcnt):
         uvar = ovar = vars[i].upper()
         if ovar in self.VAR2DB:
            var = self.VAR2DB[ovar]
         else:
            var = ovar.lower()

         if var in self.TRIMS:
            self.TRIMS[var] = 1
            self.PVALS['trmcnt'] +=1

         vinfo = self.PVALS['vinfo'][var] = self.name2number(var)
         aname = vinfo[2]
         if aname != pname:
            anames.append(aname)
            avars[aname] = []
            ovars[aname] = []
            uvars[aname] = []
            dvars[aname] = []
            aprecs[aname] = []
            imma = self.IMMAS[aname]
            attm = imma[3]
            tcodes.append("C{}".format(vinfo[0]))
            pname = aname

         avars[aname].append(var)
         ovars[aname].append(ovar)
         prec = attm[var][2]
         aprecs[aname].append(prec)
         vfld = attm[var]
         vlen = len(vfld)
         if prec > 0 and prec < 1:
            fmts[var] = self.get_float_format(prec)
            if vlen > 5:
               unit = vfld[5]
               if unit.find('deg') > -1: unit.replace('deg', '&deg;')
               uvar += "({})".format(unit)
               if vlen > 6: maxs[var] = vfld[6]
         uvars[aname].append(uvar)
         if vlen > 4 and vfld[4] == 0:
            dvars[aname].append(var)
            if var in self.FAFLDS: self.FSFLDS[var] = self.FAFLDS[var]

      self.set_full_attm_info("iuida", anames, tcodes, avars, aprecs)

      aname = "ireanqc"
      fscnts[aname] = self.set_full_attm_count(aname, "fnr")
      if fscnts[aname]:
         self.set_full_attm_info(aname, anames, tcodes, avars, aprecs)
         self.PVALS['facnt'] += 1

      aname = "iivad"
      fscnts[aname] = self.set_full_attm_count(aname, "fni")
      if fscnts[aname]:
         self.set_full_attm_info(aname, anames, tcodes, avars, aprecs)
         self.PVALS['facnt'] += 1

      # create headline and optional document 
      vhead = vcore = optattms = ''
      facnt = len(anames)
      acnt = facnt - self.PVALS['facnt'] - 1
      for i in range(acnt):
         aname = anames[i]
         vinfo = ','.join(ovars[aname])
         if vhead: vhead += ","
         vhead += vinfo
         uinfo = ','.join(uvars[aname])
         if aname in self.OPTATTMS:
            optattms += self.OPTATTMS[aname] + self.break_long_string(uinfo, 60, "<br>", 20, ",") + "</i></li></ul></li>\n"
         elif aname == 'icoreloc':
            vcore = uinfo
            if 'icorereg' not in ovars:
               self.PVALS['rinfo']['C0LIST'] = self.break_long_string(vcore, 60, "<br>", 20, ",")
         elif aname == 'icorereg':
            vcore += ',' + uinfo
            self.PVALS['rinfo']['C0LIST'] = self.break_long_string(vcore, 60, "<br>", 20, ",")
         else:
            lkey = tcodes[i] + "LIST"
            self.PVALS['rinfo'][lkey] = self.break_long_string(uinfo, 60, "<br>", 20, ",")

      # add attm Uida variables to 
      vinfo = ','.join(avars['iuida'])
      vhead += "," + vinfo.upper()
      acnt += 1

      for i in range(acnt, facnt):
         aname = anames[i]
         optattms += self.OPTATTMS[aname]
         if fscnts[aname] > 1:
            j = self.PVALS['fachar']
            for favar in self.FAVARS[aname]:
               fachar = chr(j)
               j += 1
               vinfo = ''
               for var in avars[aname]:
                  if vinfo: vinfo += ","
                  vinfo += "{}-{}".format(fachar, var.upper())
               vhead += "," + vinfo
               optattms += "<li><i>" + self.break_long_string("{} => {}: {}".format(favar, fachar, vinfo), 60, "<br>", 20, ",") + "</i></li>\n"
         else:
            favar = self.FAVARS[aname][0]
            vinfo = ''
            for var in avars[aname]:
               if vinfo: vinfo += ","
               vinfo += var.upper()
            vhead += "," + vinfo
            optattms += "<li><i>" + self.break_long_string("{}: {}".format(favar, vinfo), 60, "<br>", 20, ",") + "</i></li>\n"
         optattms += "</ul></li>\n"

      self.PVALS['vhead'] = vhead
      if optattms: self.PVALS['rinfo']['OPTATTMS'] = "{}{}</ul>".format(self.OPTATTMS['headline'], optattms)
      self.PVALS['anames'] = anames
      self.PVALS['avars'] = avars
      self.PVALS['aprecs'] = aprecs
      self.PVALS['dvars'] = dvars
      self.PVALS['fmts'] = fmts
      self.PVALS['maxs'] = maxs

      wlon = int(100*self.PVALS['lons'][0])
      elon = int(100*self.PVALS['lons'][1])
      slat = int(100*self.PVALS['lats'][0])
      nlat = int(100*self.PVALS['lats'][1])
      if wlon == 0 and elon == 36000:
         loncnd = ''
      elif wlon == elon:
         loncnd = "lon = {}".format(elon)
      elif wlon > elon:
         loncnd = "(lon >= {} OR lon <= {})".format(wlon, elon)
      elif wlon > 0 and elon < 36000:
         loncnd = " lon between {} AND {}".format(wlon, elon)
      elif elon < 36000:
         loncnd = "lon <= {}".format(elon)
      elif wlon > 0:
         loncnd = "lon >= {}".format(wlon)
      else:
         loncnd = ''

      if slat == -9000 and nlat == 9000:
         latcnd = ''
      elif slat == nlat:
         latcnd = "lat = {}".format(slat)
      elif slat > -9000 and nlat < 9000:
         latcnd = " lat between {} AND {}".format(slat, nlat)
      elif nlat < 9000:
         latcnd = "lat <= {}".format(nlat)
      else:
         latcnd = "lat >= {}".format(slat)

      if latcnd and loncnd:
         self.PVALS['spcnd'] = "{} AND {}".format(latcnd, loncnd)
      elif latcnd:
         self.PVALS['spcnd'] = latcnd
      elif loncnd:
         self.PVALS['spcnd'] = loncnd
      else:
         self.PVALS['spcnd'] = ''

      self.PVALS['fopts'] = {'OPDN' : flts[0], 'OPPT' : flts[1], 'OPSE' : flts[2],
                        'OPCQ' : flts[3], 'OPTF' : flts[4], 'OP11' : flts[5]}

   #
   # set counts for the included full attms
   #
   def set_full_attm_count(self, aname, cname):

      if aname not in self.FSSRCS: return 0

      vcnt = 0
      for sname in self.FSSRCS[aname]:
         fv = []
         fn = []
         for var in self.FASRCS[sname]:
            if var in self.FSFLDS and self.FSFLDS[var]:
               fv.append("{}-{}".format(sname, var.upper()))
               fn.append(" AND {} AND {} = {}".format(self.FACNDS[sname], cname, self.FSFLDS[var][1]))
               vcnt += 1
         if fv: self.FAVARS[aname] = fv
         if fn: self.FSCNDS[aname] = fn

      return vcnt

   #
   # set information for the included full attms
   #
   def set_full_attm_info(self, aname, anames, tcodes, avars, aprecs):

      anames.append(aname)
      imma = self.IMMAS[aname]
      attm = imma[3]
      avars[aname] = self.order_attm_variables(attm)
      if aname not in aprecs: aprecs[aname] = []
      tcodes.append("C" + imma[1])
      for var in avars[aname]:
         aprecs[aname].append(attm[var][2])

   #
   # process a validated subset request
   #
   def process_subset_request(self, ridx, rdir, rstr):

      ptcnt = self.PGRQST['ptcount']
      if ptcnt > 0:
         fname = self.PVALS['rdimma1']
         cnd = "rindex = {} AND wfile = '{}' AND status = 'O'".format(ridx, fname)
         if self.pgget("wfrqst", "", cnd): return

      self.get_subset_info(rstr)

      if ptcnt > 0:
         self.set_var_info()
         self.change_local_directory(rdir, self.LOGWRN)
         fcnt = self.build_final_files(ridx, rstr)
      else:
         fcnt = 0
         tcnt = self.get_table_info(self.PVALS['dates'])
         for i in range(tcnt):
            tidx = self.PVALS['tidx'][i]
            fdates = self.get_file_dates(self.PVALS['bdate'][i], self.PVALS['edate'][i])
            for dates in fdates:
               bdate = dates[0]
               edate = dates[1]
               pgrec = {'data_format' : 'ASCII'}
               fcnt + 1
               pgrec['disp_order'] = fcnt
               pgrec['command'] = self.pgcmd + " -f -FI"
               pgrec['cmd_detail'] = "dates={} {}&tidx={}".format(bdate, edate, tidx)
               fname = "ICOADS_R3.0_Rqst{}_{}-{}.csv".format(ridx, bdate.replace('-', ''), edate.replace('-', ''))
               self.add_request_file(ridx, fname, pgrec, self.LGEREX)

      record = {'fcount' : fcnt}
      self.pgupdt('dsrqst', record, "rindex = {}".format(ridx))

   def get_file_dates(self, bdate, edate):

      fdates = [[bdate, edate]]
      if self.TSPLIT > 1:
         dstep = int(self.diffdate(edate, bdate)/self.TSPLIT)
         if dstep > 2:
            mdate = self.adddate(bdate, 0, 0, dstep)
            while self.diffdate(edate, mdate) > 2:
               fdates[-1][1] = mdate
               bdate = self.adddate(mdate, 0, 0, 1)
               fdates.append([bdate, edate])
               mdate = self.adddate(bdate, 0, 0, dstep)
      return fdates

   #
   # process a validated subset request file
   #
   def process_subset_file(self, ridx, fidx, rdir, rstr):

      if self.PGFILE['status'] == 'O':
         self.pglog(rstr + ': Request File is built already', self.LOGWRN)
         return

      self.change_local_directory(rdir, self.LOGWRN)
      self.get_subset_info(rstr)
      self.set_var_info()
      cinfo = self.PGFILE['cmd_detail']
      tidx = 0
      dates = []
      for line in cinfo.split("&"):
         ms = re.search(r'([-\w]+)=(.+)', line)
         if not ms: continue
         token = ms.group(1)
         pstring = ms.group(2)
         if token == "dates":  # Date Limits
            dates = pstring.split(' ')
         elif token == 'tidx':
            tidx = int(pstring)

      if not (tidx and dates):
         self.pglog(rstr + ': Miss tidx or date range to build request', self.LOGWRN)

      recs = self.subset_table_index(self.PGFILE['wfile'], tidx, dates[0], dates[1])

      record = {'note' : "RECS: {}".format(recs)}
      self.pgupdt('wfrqst', record, "findex = {}".format(fidx))

   #
   # build range dates for subsetting
   #
   def build_table_file(self, fd, tidx, bdate, edate, atables):

      anames = self.PVALS['anames']
      facnt = len(anames)
      acnt = facnt - self.PVALS['facnt'] - 1

      # query on the icoreloc
      aname = anames[0]
      qcnd = "date BETWEEN '{}' AND '{}'".format(bdate, edate)
      if self.PVALS['spcnd']: qcnd += " AND " + self.PVALS['spcnd']
      tname = "{}_{}".format(aname, tidx)
      pgrecs = self.pgmget(tname, "*", qcnd, self.LGEREX)
      rcnt = len(pgrecs['iidx']) if pgrecs else 0
      recs = 0
      for r in range(rcnt):
         pgrec = {'icoreloc' : self.onerecord(pgrecs, r)}
         # quey for all attms
         qcnd = "iidx = {}".format(pgrec['icoreloc']['iidx'])
         for a in range(1, acnt):
            aname = anames[a]
            if atables[aname]:
               tname = "{}_{}".format(aname, tidx)
               pgrec[aname] = self.pgget(tname, "*", qcnd, self.LGEREX)
            else:
               pgrec[aname] = None

         # process trimming
         if 'icorereg' not in pgrec:
            aname = "icorereg"
            tname = "icorereg_{}".format(tidx)
            pgrec[aname] = self.pgget(tname, "*", qcnd, self.LGEREX)

         if 'iicoads' not in pgrec:
            aname = "iicoads"
            tname = "iicoads_{}".format(tidx)
            pgrec[aname] = self.pgget(tname, "*", qcnd, self.LGEREX)
         elif self.PVALS['iopts']:
            if self.not_match_iopts(pgrec['iicoads']): continue

         values = self.TRIMQC2(pgrec, self.PVALS['fopts'])
         if not values: continue

         if self.PVALS['trmcnt'] > 0:
            for var in values:
               if not self.TRIMS[var] or values[var]: continue
               if var == 'rh':
                  if pgrec['iimmt5'] and var in pgrec['iimmt5']:
                     pgrec['iimmt5'][var] = None
               elif pgrec['icorereg'] and var in pgrec['icorereg']:
                  pgrec['icorereg'][var] = None

         #skip empty record
         valid = 0
         for a in range(acnt):
            aname = anames[a]
            record = pgrec[aname]
            dvars = self.PVALS['dvars'][aname]
            if not (dvars and record): continue
            for var in dvars:
               if var in record and record[var] != None:
                  if isinstance(record[var], int) or len(record[var]) > 0:
                     valid = 1
                     break
            if valid: break

         if not valid: continue

         buf = ''
         # save each attm values 
         for a in range(acnt):
            aname = anames[a]
            buf += self.join_attm_fields(aname, pgrec[aname]) + ","

         # get and save Uida attm values
         aname = "iuida"
         tname = "iuida_{}".format(tidx)
         record = self.pgget(tname, "*", qcnd, self.LGEREX)
         buf += self.join_attm_fields(aname, record)

         # get and save full attm values
         for a in range(acnt+1, facnt):
            aname = anames[a]
            tname = "{}_{}".format(aname, tidx)
            for cnd in self.FSCNDS[aname]:
               if atables[aname]:
                  record = self.pgget(tname, "*", qcnd + cnd, self.LGEREX)
               else:
                  record = None

               buf += ',' + self.join_attm_fields(aname, record)

         buf += "\n"
         fd.write(buf)
         recs += 1

      return recs

   #
   # check if not matching options
   #
   def not_match_iopts(self, pgrec):

      if self.PVALS['pts'] and not (pgrec['pt'] and pgrec['pt'] in self.PVALS['pts']): return 1
      if self.PVALS['dcks'] and not (pgrec['dck'] and pgrec['dck'] in self.PVALS['dcks']): return 1
      if self.PVALS['sids'] and not (pgrec['sid'] and pgrec['sid'] in self.PVALS['sids']): return 1

      return 0  # matched

   #
   # join the attm fields to generate a string
   #
   def join_attm_fields(self, aname, record):

      fmts = self.PVALS['fmts']
      maxs = self.PVALS['maxs']
      vars = self.PVALS['avars'][aname]
      precs = self.PVALS['aprecs'][aname]
      vcnt = len(vars)
      if not record: return ','.join(['']*vcnt)

      sret = ''
      for v in range(vcnt):
         if v: sret += ','
         var = vars[v]
         val = record[var]
         if val is None: continue
         fmt = '{}'
         if precs[v] == 0:
            if var == 'id' and val.find(',') > -1: fmt = '"{}"'
         elif precs[v] != 1:
            if var not in maxs or val < maxs[var]:
               val *= precs[v]
               if var in fmts: fmt = fmts[var]
         sret += fmt.format(val)

      return sret

   #
   # subset data and save in fname
   #
   def subset_table_index(self, fname, tidx, bdate, edate):

      atables = {}
      self.set_scname(dbname = 'ivaddb', scname = 'ivaddb', lnname = 'ivaddb', dbhost = self.PGLOG['PMISCHOST'])

      tname = "cntldb.iattm"
      for aname in self.PVALS['anames']:
         cnd = f"tidx = {tidx} AND attm = '{aname}'"
         atables[aname] = self.pgget(tname, "", cnd, self.LGEREX)

      dstep = int(self.diffdate(edate, bdate)/self.PSTEP)
      if dstep == 0: dstep = 1
      self.pgsystem("echo '{}' > {}".format(self.PVALS['vhead'], fname), self.LGWNEX, 1029)
      fd = open(fname, 'a')
      recs = 0
      while bdate <= edate:
         pdate = self.adddate(bdate, 0, 0, dstep)
         if pdate > edate: pdate = edate
         recs += self.build_table_file(fd, tidx, bdate, pdate, atables)
         bdate = self.adddate(pdate, 0, 0, 1)

      fd.close()

      self.dssdb_scname()
      return recs

   #
   # build the final subset files
   #
   def build_final_files(self, ridx, rstr):

      self.dssdb_scname()

      fcnt = self.pgget('wfrqst', '', "rindex = {} AND type = 'D'".format(ridx))
      fname = self.write_readme()
      pgrec = {'status' : 'O', 'type' : 'O', 'data_format' : 'PDF'}
      fcnt += 1
      pgrec['disp_order'] = fcnt
      self.add_request_file(ridx, fname, pgrec, self.LGEREX)

      fname = self.PVALS['rdimma1']
      pgrec = {'status' : 'O', 'type' : 'S', 'data_format' : 'FORTRAN'}
      fcnt += 1
      pgrec['disp_order'] = fcnt
      self.local_copy_local(fname, self.PVALS['codedir'] + fname, self.LGEREX)
      self.add_request_file(ridx, fname, pgrec, self.LGEREX)

      return fcnt

   #
   # process reqest info, create command file and the input file list
   #
   def get_subset_info(self, rstr):


      rinfo = self.PGRQST['rinfo'] if self.PGRQST['rinfo'] else self.PGRQST['note']
      cnt = 0
      for line in rinfo.split("&"):
         ms = re.search(r'([-\w]+)=(.+)', line)
         if not ms: continue
         token = ms.group(1)
         pstring = ms.group(2)
         if token == "dates":  # Date Limits
            self.PVALS['rinfo']['DATES'] = pstring
            self.PVALS['dates'] = pstring.split(' ')
            if len(self.PVALS['dates']) == 2: cnt += 1
         elif token == 'lats':
            self.PVALS['lats'] = self.get_latitudes(pstring, self.PVALS['resol'])
            self.PVALS['rinfo']['LATS'] = "{}, {}".format(self.PVALS['lats'][0], self.PVALS['lats'][1])
            cnt += 1
         elif token == 'lons':
            self.PVALS['lons'] = self.get_longitudes(pstring, self.PVALS['resol'])
            self.PVALS['rinfo']['LONS'] = "{}, {}".format(self.PVALS['lons'][0], self.PVALS['lons'][1])
            cnt += 1
         elif token == 'flts':    # Filter Options
            sflts = pstring.split(' ')
            self.PVALS['flts'] = [int(sflt) for sflt in sflts]
            self.PVALS['rinfo']['FLTLIST'] = "</td><td>".join(sflts)
            cnt += 1
         elif token == 'vars':  # Variable Names
            self.PVALS['vars'] = pstring.split(', ')
            cnt += 1
         elif token == 'pts':  # platform ids
            self.PVALS['iopts'] += 1
            self.PVALS['pts'] = list(map(int, pstring.split(', ')))
            cnt += 1
         elif token == 'dcks':  # Deck ids
            self.PVALS['iopts'] += 1
            self.PVALS['dcks'] = list(map(int, pstring.split(', ')))
            cnt += 1
         elif token == 'sids':  # source ids
            self.PVALS['iopts'] += 1
            self.PVALS['sids'] = list(map(int, pstring.split(', ')))
            cnt += 1
         elif token == 'Rean-qc':
            self.FSSRCS['ireanqc'] = pstring.split(', ')
         elif token == 'Ivad':
            self.FSSRCS['iivad'] = pstring.split(', ')

      if cnt < 5: self.pglog(rstr + ": Incomplete request control information", self.LGEREX)

      if self.PVALS['iopts'] > 1: self.TSPLIT *= 2
      if (self.PVALS['lats'][1] - self.PVALS['lats'][0]) > 90.0: self.TSPLIT *= 2
      if (self.PVALS['lons'][1] - self.PVALS['lons'][0]) > 180.0: self.TSPLIT *= 2

   #
   # write a HTML readme file, and convert it to PDF format
   #
   def write_readme(self):

      user = self.get_ruser_names(self.PGRQST['email'])
      readme = self.PVALS['readme'] + self.PGRQST['rqstid'].lower()
      rinfo = self.PVALS['rinfo']
      readtmp = self.PVALS['codedir'] + self.PVALS['readhtml']

      self.pglog("Create Readme file " + readme, self.LOGWRN)
      readhtml = readme + ".html"
      URM = open(readhtml, 'w')
      RHTML = open(readtmp, 'r')
      rinfo['CURDATE'] = self.curdate("D Month YYYY")
      rinfo['ACCDATE'] = self.curdate()
      rinfo['USER'] = "{} [{}]".format(user['name'], self.PGRQST['email'])

      line = RHTML.readline()
      while line:
         if re.match(r'^#', line): continue  # skip comment line
         ms = re.search(r'__(\w+)__', line)
         if ms:
            key = ms.group(1)
            rep = "__{}__".format(key)
            if key in rinfo:
               line = line.replace(rep, rinfo[key])
            else:
               line = line.replace(rep, '')
         URM.write(line)
         line = RHTML.readline()

      RHTML.close()
      URM.close()

      readpdf = readme + ".pdf"
      self.pgsystem("{} {} {}".format(self.PVALS['html2pdf'], readhtml, readpdf), self.LOGWRN, 35)
      if not self.check_local_file(readpdf):
         self.pglog("{}: Error convert {} to {}".format(self.PVALS['html2pdf'], readhtml, readpdf), self.LOGWRN)

      self.delete_local_file(readhtml, self.LGWNEX)

      return readpdf

# main function to execute this script
def main():
   Imma1Subset().main()

# call main() to start program
if __name__ == "__main__": main()
