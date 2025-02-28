#!/usr/bin/env python3
#
##################################################################################
#
#     Title : imma1_subset
#    Author : Zaihua Ji, zji@ucar.edu
#      Date : 01/04/2021
#            2025-02-18 transferred to package rda_python_icoads from
#            https://github.com/NCAR/rda-icoads.git
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
from rda_python_common import PgLOG
from rda_python_common import PgDBI
from rda_python_common import PgSIG
from rda_python_common import PgUtil
from rda_python_common import PgFile
from rda_python_common import PgOPT
from rda_python_dsrqst import PgSubset
from . import PgIMMA

IDSID = 'd548000'
VAR2DB = {'IS' : "ics"}
PVALS = {
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

FAVARS = {}  # hash of ireanqc and iivad, values are selected source name-var
FSFLDS = {}  # hash of selected data variables in FACNDS
FSSRCS = {}  # hash of ireanqc and iivad, values are array of selected source names
FSCNDS = {}  # hash of ireanqc and iivad, values are array of conditions for variables in FSFLDS
FACNDS = {
   'ERA-20C' : 'dprp = 1',
   'CERA-20C' : 'dprp = 2',
   'FS01' : "arci = 'FS01'",
   'BKT' : "arci = ' BKT'"
}   # additional condition for full attm
FAFLDS = {'d' : [0, 18], 'w' : [0, 20], 'slp' : [0, 25], 'at' : [0, 29]}
FASRCS = {
   'ERA-20C' : ['d', 'w', 'slp', 'at'],
   'CERA-20C' : ['d', 'w', 'slp', 'at'],
   'FS01' : ['w'],
   'BKT' : ['at']
}

TRIMS = {'sst' : 0, 'at' : 0, 'd' : 0, 'w' : 0, 'slp' : 0, 'wbt' : 0, 'dpt' : 0, 'rh' : 0}

# Optional attms for subset. Append var-list to Replace <OPTATTMS> in the README template file
OPTATTMS = {
   'headline' : "<h2>Details for optional selections</h2>\n<ul>\n",
   'iimmt5' : "<li>P/V <i>Immt</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=37\">Table C5, page 37</a>\n<ul><li><i>\n",
   'imodqc' : "<li>P/V <i>Mod-qc</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=38\">Table C6, page 38</a>\n<ul><li><i>\n",
   'imetavos' : "<li>P/V <i>Meta-vos</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=39\">Table C7, page 39</a><ul><li><i>\n",
   'inocn' : "<li>P/V <i>Nocn</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=40\">Table C8, page 40</a><ul><li><i>\n",
   'iecr' : "<li>P/V <i>Ecr</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=41\">Table C9, page 41</a><ul><li><i>\n",
   'ireanqc' : "<li>P/V <i>Rean-qc</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=42\">Table C95, page 42</a><ul>\n",
   'iivad' : "<li>P/V <i>Ivad</i>, <a href=\"http://rda.ucar.edu/datasets/" + IDSID + "/docs/R3.0-imma1.pdf#page=43\">Table C96, page 43</a><ul>\n"
}

PGRQST = PGFILE = None
pgcmd = 'imma1_subset'
PSTEP = 32

#
# main function to run dsarch
#
def main():

   global PGRQST, PGFILE

   PgLOG.PGLOG['LOGFILE'] = "icoads.log"
   argv = sys.argv[1:]
   option = rdir = None
   fidx = ridx = 0

   for arg in argv:
      if arg == "-b":
         PgLOG.PGLOG['BCKGRND'] = 1
      elif arg == "-d":
         PgLOG.PGLOG['DBGLEVEL'] = 1000
      elif arg == "-f":
         option = 'f'
      elif re.match(r'^-', arg):
         PgLOG.pglog(arg + ": Unknown Option", PgLOG.LGEREX)
      elif option and option == 'f':
         fidx = int(arg)
         option = None
      elif re.match(r'^(\d+)$', arg):
         if ridx == 0:
            ridx = int(arg)
         else:
            PgLOG.pglog("{}: Request Index ({}) given already".format(arg, ridx), PgLOG.LGEREX)
      else:
         if rdir: PgLOG.pglog("{}: Request Directory ({}) given already".format(arg, rdir), PgLOG.LGEREX)
         rdir = arg

   PgLOG.cmdlog("{} {}".format(pgcmd, ' '.join(argv)))
   PgDBI.dssdb_scname()
   if fidx:
      fcnd = "findex = {}".format(fidx)
      PGFILE = PgDBI.pgget('wfrqst', '*', fcnd, PgLOG.LGEREX)
      if not PGFILE: PgLOG.pglog(fcnd + ": Request File Not in RDADB", PgLOG.LGEREX)
      if ridx == 0: ridx = PGFILE['rindex']
   PGRQST = PgSubset.valid_subset_request(ridx, rdir, IDSID, PgLOG.LGWNEX)
   if not rdir: rdir = PgLOG.join_paths(PgLOG.PGLOG['RQSTHOME'], PGRQST['rqstid'])
   rstr = "{}-Rqst{}".format(PGRQST['dsid'], ridx)
   if fidx > 0: rstr += "-" + PGFILE['wfile']

   if fidx:
      process_subset_file(ridx, fidx, rdir, rstr)
   else:
      process_subset_request(ridx, rdir, rstr)

   PgLOG.cmdlog()
   sys.exit(0)

#
# set the table info array
#
def get_table_info(dates):

   bdate = PgUtil.validate_date(dates[0])
   edate = PgUtil.validate_date(dates[1])
   cnd = "bdate <= '{}' AND edate >= '{}'".format(edate, bdate)
   pgrecs = PgDBI.pgmget('itable', "tidx, bdate, edate", cnd + " ORDER BY tidx", PgLOG.LGEREX)
   tcnt = len(pgrecs['tidx']) if pgrecs else 0
   if not tcnt: PgLOG.pglog("No table index found in dssdb.itable for " + cnd, PgLOG.LGEREX)
   PVALS['tidx'] = pgrecs['tidx']
   PVALS['bdate'] = [bdate]
   PVALS['bdate'].extend([str(d) for d in pgrecs['bdate'][1:]])
   PVALS['edate'] = [str(d) for d in pgrecs['edate'][:-1]]
   PVALS['edate'].append(edate)

   return tcnt

#
# get the float format string
#
def get_float_format(resl):

   prec = 0
   while resl < 1:
      prec += 1
      resl *=10

   return r'{:.%df}' % prec if prec else ''

#
# set variable information
#
def set_var_info():
   
   vars = PVALS['vars']
   flts = PVALS['flts']
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
      if ovar in VAR2DB:
         var = VAR2DB[ovar]
      else:
         var = ovar.lower()

      if var in TRIMS:
         TRIMS[var] = 1
         PVALS['trmcnt'] +=1

      vinfo = PVALS['vinfo'][var] = PgIMMA.name2number(var)
      aname = vinfo[2]
      if aname != pname:
         anames.append(aname)
         avars[aname] = []
         ovars[aname] = []
         uvars[aname] = []
         dvars[aname] = []
         aprecs[aname] = []
         imma = PgIMMA.IMMAS[aname]
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
         fmts[var] = get_float_format(prec)
         if vlen > 5:
            unit = vfld[5]
            if unit.find('deg') > -1: unit.replace('deg', '&deg;')
            uvar += "({})".format(unit)
            if vlen > 6: maxs[var] = vfld[6]
      uvars[aname].append(uvar)
      if vlen > 4 and vfld[4] == 0:
         dvars[aname].append(var)
         if var in FAFLDS: FSFLDS[var] = FAFLDS[var]

   set_full_attm_info("iuida", anames, tcodes, avars, aprecs)

   aname = "ireanqc"
   fscnts[aname] = set_full_attm_count(aname, "fnr")
   if fscnts[aname]:
      set_full_attm_info(aname, anames, tcodes, avars, aprecs)
      PVALS['facnt'] += 1

   aname = "iivad"
   fscnts[aname] = set_full_attm_count(aname, "fni")
   if fscnts[aname]:
      set_full_attm_info(aname, anames, tcodes, avars, aprecs)
      PVALS['facnt'] += 1

   # create headline and optional document 
   vhead = vcore = optattms = ''
   facnt = len(anames)
   acnt = facnt - PVALS['facnt'] - 1
   for i in range(acnt):
      aname = anames[i]
      vinfo = ','.join(ovars[aname])
      if vhead: vhead += ","
      vhead += vinfo
      uinfo = ','.join(uvars[aname])
      if aname in OPTATTMS:
         optattms += OPTATTMS[aname] + PgLOG.break_long_string(uinfo, 60, "<br>", 20, ",") + "</i></li></ul></li>\n"
      elif aname == 'icoreloc':
         vcore = uinfo
         if 'icorereg' not in ovars:
            PVALS['rinfo']['C0LIST'] = PgLOG.break_long_string(vcore, 60, "<br>", 20, ",")
      elif aname == 'icorereg':
         vcore += ',' + uinfo
         PVALS['rinfo']['C0LIST'] = PgLOG.break_long_string(vcore, 60, "<br>", 20, ",")
      else:
         lkey = tcodes[i] + "LIST"
         PVALS['rinfo'][lkey] = PgLOG.break_long_string(uinfo, 60, "<br>", 20, ",")

   # add attm Uida variables to 
   vinfo = ','.join(avars['iuida'])
   vhead += "," + vinfo.upper()
   acnt += 1

   for i in range(acnt, facnt):
      aname = anames[i]
      optattms += OPTATTMS[aname]
      if fscnts[aname] > 1:
         j = PVALS['fachar']
         for favar in FAVARS[aname]:
            fachar = chr(j)
            j += 1
            vinfo = ''
            for var in avars[aname]:
               if vinfo: vinfo += ","
               vinfo += "{}-{}".format(fachar, var.upper())
            vhead += "," + vinfo
            optattms += "<li><i>" + PgLOG.break_long_string("{} => {}: {}".format(favar, fachar, vinfo), 60, "<br>", 20, ",") + "</i></li>\n"
      else:
         favar = FAVARS[aname][0]
         vinfo = ''
         for var in avars[aname]:
            if vinfo: vinfo += ","
            vinfo += var.upper()
         vhead += "," + vinfo
         optattms += "<li><i>" + PgLOG.break_long_string("{}: {}".format(favar, vinfo), 60, "<br>", 20, ",") + "</i></li>\n"
      optattms += "</ul></li>\n"

   PVALS['vhead'] = vhead
   if optattms: PVALS['rinfo']['OPTATTMS'] = "{}{}</ul>".format(OPTATTMS['headline'], optattms)
   PVALS['anames'] = anames
   PVALS['avars'] = avars
   PVALS['aprecs'] = aprecs
   PVALS['dvars'] = dvars
   PVALS['fmts'] = fmts
   PVALS['maxs'] = maxs

   wlon = int(100*PVALS['lons'][0])
   elon = int(100*PVALS['lons'][1])
   slat = int(100*PVALS['lats'][0])
   nlat = int(100*PVALS['lats'][1])
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
      PVALS['spcnd'] = "{} AND {}".format(latcnd, loncnd)
   elif latcnd:
      PVALS['spcnd'] = latcnd
   elif loncnd:
      PVALS['spcnd'] = loncnd
   else:
      PVALS['spcnd'] = ''

   PVALS['fopts'] = {'OPDN' : flts[0], 'OPPT' : flts[1], 'OPSE' : flts[2],
                     'OPCQ' : flts[3], 'OPTF' : flts[4], 'OP11' : flts[5]}

#
# set counts for the included full attms
#
def set_full_attm_count(aname, cname):

   if aname not in FSSRCS: return 0

   vcnt = 0
   for sname in FSSRCS[aname]:
      fv = []
      fn = []
      for var in FASRCS[sname]:
         if var in FSFLDS and FSFLDS[var]:
            fv.append("{}-{}".format(sname, var.upper()))
            fn.append(" AND {} AND {} = {}".format(FACNDS[sname], cname, FSFLDS[var][1]))
            vcnt += 1
      if fv: FAVARS[aname] = fv
      if fn: FSCNDS[aname] = fn

   return vcnt

#
# set information for the included full attms
#
def set_full_attm_info(aname, anames, tcodes, avars, aprecs):

   anames.append(aname)
   imma = PgIMMA.IMMAS[aname]
   attm = imma[3]
   avars[aname] = PgIMMA.order_attm_variables(attm)
   if aname not in aprecs: aprecs[aname] = []
   tcodes.append("C" + imma[1])
   for var in avars[aname]:
      aprecs[aname].append(attm[var][2])

#
# process a validated subset request
#
def process_subset_request(ridx, rdir, rstr):

   ptcnt = PGRQST['ptcount']
   if ptcnt > 0:
      fname = PVALS['rdimma1']
      cnd = "rindex = {} AND wfile = '{}' AND status = 'O'".format(ridx, fname)
      if PgDBI.pgget("wfrqst", "", cnd): return

   get_subset_info(rstr)
   
   if ptcnt > 0:
      set_var_info()
      PgFile.change_local_directory(rdir, PgLOG.LOGWRN)
      fcnt = build_final_files(ridx, rstr)
   else:
      fcnt = get_table_info(PVALS['dates'])
      for i in range(fcnt):
         bdate = PVALS['bdate'][i]
         edate = PVALS['edate'][i]
         tidx = PVALS['tidx'][i]
         pgrec = {}
         pgrec['data_format'] = 'ASCII'
         pgrec['disp_order'] = i+1
         pgrec['command'] = pgcmd + " -f -FI"
         pgrec['cmd_detail'] = "dates={} {}&tidx={}".format(bdate, edate, tidx)
         fname = "ICOADS_R3.0_Rqst{}_{}-{}.csv".format(ridx, bdate.replace('-', ''), edate.replace('-', ''))
         PgSubset.add_request_file(ridx, fname, pgrec, PgLOG.LGEREX)

   record = {'fcount' : fcnt}
   PgDBI.pgupdt('dsrqst', record, "rindex = {}".format(ridx))

#
# process a validated subset request file
#
def process_subset_file(ridx, fidx, rdir, rstr):

   if PGFILE['status'] == 'O':
      PgLOG.pglog(rstr + ': Request File is built already', PgLOG.LOGWRN)
      return

   PgFile.change_local_directory(rdir, PgLOG.LOGWRN)
   get_subset_info(rstr)
   set_var_info()
   cinfo = PGFILE['cmd_detail']
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
      PgLOG.pglog(rstr + ': Miss tidx or date range to build request', PgLOG.LOGWRN)

   recs = subset_table_index(PGFILE['wfile'], tidx, dates[0], dates[1])

   record = {'note' : "RECS: {}".format(recs)}
   PgDBI.pgupdt('wfrqst', record, "findex = {}".format(fidx))

#
# build range dates for subsetting
#
def build_table_file(fd, tidx, bdate, edate, atables):

   anames = PVALS['anames']
   facnt = len(anames)
   acnt = facnt - PVALS['facnt'] - 1

   # query on the icoreloc
   aname = anames[0]
   qcnd = "date BETWEEN '{}' AND '{}'".format(bdate, edate)
   if PVALS['spcnd']: qcnd += " AND " + PVALS['spcnd']
   tname = "{}_{}".format(aname, tidx)
   pgrecs = PgDBI.pgmget(tname, "*", qcnd, PgLOG.LGEREX)
   rcnt = len(pgrecs['iidx']) if pgrecs else 0
   recs = 0
   for r in range(rcnt):
      pgrec = {'icoreloc' : PgUtil.onerecord(pgrecs, r)}
      # quey for all attms
      qcnd = "iidx = {}".format(pgrec['icoreloc']['iidx'])
      for a in range(1, acnt):
         aname = anames[a]
         if atables[aname]:
            tname = "{}_{}".format(aname, tidx)
            pgrec[aname] = PgDBI.pgget(tname, "*", qcnd, PgLOG.LGEREX)
         else:
            pgrec[aname] = None

      # process trimming
      if 'icorereg' not in pgrec:
         aname = "icorereg"
         tname = "icorereg_{}".format(tidx)
         pgrec[aname] = PgDBI.pgget(tname, "*", qcnd, PgLOG.LGEREX)

      if 'iicoads' not in pgrec:
         aname = "iicoads"
         tname = "iicoads_{}".format(tidx)
         pgrec[aname] = PgDBI.pgget(tname, "*", qcnd, PgLOG.LGEREX)
      elif PVALS['iopts']:
         if not_match_iopts(pgrec['iicoads']): continue

      values = PgIMMA.TRIMQC2(pgrec, PVALS['fopts'])
      if not values: continue

      if PVALS['trmcnt'] > 0:
         for var in values:
            if not TRIMS[var] or values[var]: continue
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
         dvars = PVALS['dvars'][aname]
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
         buf += join_attm_fields(aname, pgrec[aname]) + ","

      # get and save Uida attm values
      aname = "iuida"
      tname = "iuida_{}".format(tidx)
      record = PgDBI.pgget(tname, "*", qcnd, PgLOG.LGEREX)
      buf += join_attm_fields(aname, record)

      # get and save full attm values
      for a in range(acnt+1, facnt):
         aname = anames[a]
         tname = "{}_{}".format(aname, tidx)
         for cnd in FSCNDS[aname]:
            if atables[aname]:
               record = PgDBI.pgget(tname, "*", qcnd + cnd, PgLOG.LGEREX)
            else:
               record = None

            buf += ',' + join_attm_fields(aname, record)

      buf += "\n"
      fd.write(buf)
      recs += 1

   return recs

#
# check if not matching options
#
def not_match_iopts(pgrec):
   
   if PVALS['pts'] and not (pgrec['pt'] and pgrec['pt'] in PVALS['pts']): return 1
   if PVALS['dcks'] and not (pgrec['dck'] and pgrec['dck'] in PVALS['dcks']): return 1
   if PVALS['sids'] and not (pgrec['sid'] and pgrec['sid'] in PVALS['sids']): return 1

   return 0  # matched

#
# join the attm fields to generate a string
#
def join_attm_fields(aname, record):

   fmts = PVALS['fmts']
   maxs = PVALS['maxs']
   vars = PVALS['avars'][aname]
   precs = PVALS['aprecs'][aname]
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
def subset_table_index(fname, tidx, bdate, edate):

   atables = {}
   PgDBI.ivaddb_scname()

   for aname in PVALS['anames']:
      atables[aname] = PgDBI.pgget('cntldb.iattm', "", "tidx = {} AND attm = '{}'".format(tidx, aname), PgLOG.LGEREX)

   dstep = int(PgUtil.diffdate(edate, bdate)/PSTEP)
   if dstep == 0: dstep = 1
   PgLOG.pgsystem("echo '{}' > {}".format(PVALS['vhead'], fname), PgLOG.LGWNEX, 1029)
   fd = open(fname, 'a')
   recs = 0
   while bdate <= edate:
      pdate = PgUtil.adddate(bdate, 0, 0, dstep)
      if pdate > edate: pdate = edate
      recs += build_table_file(fd, tidx, bdate, pdate, atables)
      bdate = PgUtil.adddate(pdate, 0, 0, 1)

   fd.close()

   PgDBI.dssdb_scname()
   return recs
  
#
# build the final subset files
#
def build_final_files(ridx, rstr):

   PgDBI.dssdb_scname()

   fcnt = PgDBI.pgget('wfrqst', '', "rindex = {} AND type = 'D'".format(ridx))
   fname = write_readme()
   pgrec = {'status' : 'O', 'type' : 'O', 'data_format' : 'PDF'}
   fcnt += 1
   pgrec['disp_order'] = fcnt
   PgSubset.add_request_file(ridx, fname, pgrec, PgLOG.LGEREX)

   fname = PVALS['rdimma1']
   pgrec = {'status' : 'O', 'type' : 'S', 'data_format' : 'FORTRAN'}
   fcnt += 1
   pgrec['disp_order'] = fcnt
   PgFile.local_copy_local(fname, PVALS['codedir'] + fname, PgLOG.LGEREX)
   PgSubset.add_request_file(ridx, fname, pgrec, PgLOG.LGEREX)

   return fcnt

#
# process reqest info, create command file and the input file list
#
def get_subset_info(rstr):

   rinfo = PGRQST['rinfo'] if PGRQST['rinfo'] else PGRQST['note']
   cnt = 0
   for line in rinfo.split("&"):
      ms = re.search(r'([-\w]+)=(.+)', line)
      if not ms: continue
      token = ms.group(1)
      pstring = ms.group(2)
      if token == "dates":  # Date Limits
         PVALS['rinfo']['DATES'] = pstring
         PVALS['dates'] = pstring.split(' ')
         if len(PVALS['dates']) == 2: cnt += 1
      elif token == 'lats':
         PVALS['lats'] = PgSubset.get_latitudes(pstring, PVALS['resol'])
         PVALS['rinfo']['LATS'] = "{}, {}".format(PVALS['lats'][0], PVALS['lats'][1])
         cnt += 1
      elif token == 'lons':
         PVALS['lons'] = PgSubset.get_longitudes(pstring, PVALS['resol'])
         PVALS['rinfo']['LONS'] = "{}, {}".format(PVALS['lons'][0], PVALS['lons'][1])
         cnt += 1
      elif token == 'flts':    # Filter Options
         sflts = pstring.split(' ')
         PVALS['flts'] = [int(sflt) for sflt in sflts]
         PVALS['rinfo']['FLTLIST'] = "</td><td>".join(sflts)
         cnt += 1
      elif token == 'vars':  # Variable Names
         PVALS['vars'] = pstring.split(', ')
         cnt += 1
      elif token == 'pts':  # platform ids
         PVALS['iopts'] += 1
         PVALS['pts'] = list(map(int, pstring.split(', ')))
         cnt += 1
      elif token == 'dcks':  # Deck ids
         PVALS['iopts'] += 1
         PVALS['dcks'] = list(map(int, pstring.split(', ')))
         cnt += 1
      elif token == 'sids':  # source ids
         PVALS['iopts'] += 1
         PVALS['sids'] = list(map(int, pstring.split(', ')))
         cnt += 1
      elif token == 'Rean-qc':
         FSSRCS['ireanqc'] = pstring.split(', ')
      elif token == 'Ivad':
         FSSRCS['iivad'] = pstring.split(', ')

   if cnt < 5: PgLOG.pglog(rstr + ": Incomplete request control information", PgLOG.LGEREX)

#
# write a HTML readme file, and convert it to PDF format
#
def write_readme():

   user = PgDBI.get_ruser_names(PGRQST['email'])
   readme = PVALS['readme'] + PGRQST['rqstid'].lower()
   rinfo = PVALS['rinfo']
   readtmp = PVALS['codedir'] + PVALS['readhtml']

   PgLOG.pglog("Create Readme file " + readme, PgLOG.LOGWRN)
   readhtml = readme + ".html"
   URM = open(readhtml, 'w')
   RHTML = open(readtmp, 'r')
   rinfo['CURDATE'] = PgUtil.curdate("D Month YYYY")
   rinfo['ACCDATE'] = PgUtil.curdate()
   rinfo['USER'] = "{} [{}]".format(user['name'], PGRQST['email'])

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
   PgLOG.pgsystem("{} {} {}".format(PVALS['html2pdf'], readhtml, readpdf), PgLOG.LOGWRN, 35)
   if not PgFile.check_local_file(readpdf):
      PgLOG.pglog("{}: Error convert {} to {}".format(PVALS['html2pdf'], readhtml, readpdf), PgLOG.LOGWRN)

   PgFile.delete_local_file(readhtml, PgLOG.LGWNEX)

   return readpdf

#
# call main() to start program
#
if __name__ == "__main__": main()
