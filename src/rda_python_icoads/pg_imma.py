#
###############################################################################
#
#      Title : pg_imma.py
#     Author : Zaihua Ji,  zji@car.edu
#       Date : 09/13/2020
#             2025-02-18 transferred to package rda_python_icoads from
#             https://github.com/NCAR/rda-shared-libraries.git
#             2026-09-04 convert to class PgIMMA
#    Purpose : python library module defining IMMA data
#
#    Github : https://github.com/NCAR/rda-python-icoads.git
#
###############################################################################
#
import os
import re
import math
import numpy
from rda_python_common.pg_opt import PgOPT

class PgIMMA(PgOPT):

   def __init__(self):
      super().__init__()
      # variable definition for each section
      # PREC: 0 - string, 1 - integer, otherwise - float
      # TYPE: 0 - data element
      #       1 - time/location/identity element
      #       2 - IMMA format element
      #       3 - indicator element
      #       4 - QC element(s)
      self.ICORELOC = {   #total length = 45
      #          IDX SIZE  PREC POS TYPE UNIT   Description
         'yr' : [0,  4,    1,   0,  1],         #Year
         'mo' : [1,  2,    1,   4,  1],         #Month
         'dy' : [2,  2,    1,   6,  1],         #Day
         'hr' : [3,  4, 0.01,   8,  1],         #Hour
        'lat' : [4,  5, 0.01,  12,  1, "degN"], #Latitude
        'lon' : [5,  6, 0.01,  17,  1, "degE"], #Longitude
         'im' : [6,  2,    1,  23,  2],         #IMMA Version
       'attc' : [7,  1,    0,  25,  2],         #Attm Count
         'ti' : [8,  1,    1,  26,  3],         #Time Indicator
         'li' : [9,  1,    1,  27,  3],         #Latitude/Longitude Indicator
         'ds' : [10, 1,    1,  28,  0],         #Ship Course
         'vs' : [11, 1,    1,  29,  0],         #Ship Speed
        'nid' : [12, 2,    1,  30,  1],         #National Source Indicator
         'ii' : [13, 2,    1,  32,  3],         #ID Indicator
         'id' : [14, 9,    0,  34,  1],         #Identification/Call sign
         'c1' : [15, 2,    0,  43,  1]          #Country Code
      }
      self.ICOREREG = {   #total length = 63
      #          IDX SIZE  PREC POS TYPE UNIT   MAX Description
         'di' : [0,  1,    1,   0,  3],             #Wind Direction Indicator
          'd' : [1,  3,    1,   1,  0,  "deg"],     #Wind Direction
         'wi' : [2,  1,    1,   4,  3],             #Wind Speed Indicator
          'w' : [3,  3,  0.1,   5,  0,  "m/s"],     #Wind Speed
         'vi' : [4,  1,    1,   8,  3],             #VV Indicator
         'vv' : [5,  2,    1,   9,  0],             #Visibility
         'ww' : [6,  2,    1,  11,  0],             #Present Weather
         'w1' : [7,  1,    1,  13,  0],             #Past Weather
        'slp' : [8,  5,  0.1,  14,  0,  "hPa"],     #Sea Level Pressure
          'a' : [9,  1,    1,  19,  3],             #Characteristic of PPP
        'ppp' : [10, 3,  0.1,  20,  0,  "hPa"],     #Amount of Pressure Tendency
         'it' : [11, 1,    1,  23,  3],             #Temperature Indicator
         'at' : [12, 4,  0.1,  24,  0, "degC"],     #Air Temperature
       'wbti' : [13, 1,    1,  28,  3],             #WBT Indicator
        'wbt' : [14, 4,  0.1,  29,  0, "degC"],     #Wet-Bulb Temperature
       'dpti' : [15, 1,    1,  33,  3],             #DPT Indicator
        'dpt' : [16, 4,  0.1,  34,  0, "degC"],     #Dew-Point Tmperature
         'si' : [17, 2,    1,  38,  3],             #SST Measure Method
        'sst' : [18, 4,  0.1,  40,  0, "degC"],     #Sea Surface Temperature 
          'n' : [19, 1,    1,  44,  0],             #Total Cloud Amount
         'nh' : [20, 1,    1,  45,  0],             #Lower Cloud Amount
         'cl' : [21, 1,    0,  46,  3],             #Low Cloud Type
         'hi' : [22, 1,    1,  47,  3],             #H Indicator
          'h' : [23, 1,    0,  48,  0],             #Cloud Height
         'cm' : [24, 1,    0,  49,  3],             #Middle Cloud Type
         'ch' : [25, 1,    0,  50,  3],             #High Cloud type
         'wd' : [26, 2,   10,  51,  0],             #Wave Direction
         'wp' : [27, 2,    1,  53,  0,    "s"],     #Wave Period
         'wh' : [28, 2,  0.5,  55,  0,    "m", 99], #Wave Height
         'sd' : [29, 2,   10,  57,  0],             #Swell Direction
         'sp' : [30, 2,    1,  59,  0,    "s"],     #Swell Period
         'sh' : [31, 2,  0.5,  61,  0,    "m", 99]  #Swell Height
      }
      self.IICOADS = {   # atti = ' 1', attl = 65
      #          IDX SIZE PREC POS TYPE Description
        'bsi' : [0,  1,   1,   4,  3],  #Box System Indicator
        'b10' : [1,  3,   1,   5,  1],  #10 Deg Box Number
         'b1' : [2,  2,   1,   8,  1],  #1 Deg Box Number
        'dck' : [3,  3,   1,  10,  1],  #Deck
        'sid' : [4,  3,   1,  13,  1],  #Source ID
         'pt' : [5,  2,   1,  16,  1],  #Platform Type
       'dups' : [6,  2,   1,  18,  3],  #Dup Status
       'dupc' : [7,  1,   1,  20,  3],  #Dup Check
         'tc' : [8,  1,   1,  21,  3],  #Track Check
         'pb' : [9,  1,   1,  22,  3],  #Pressure Bias
         'wx' : [10, 1,   1,  23,  3],  #Wave Period Indicator
         'sx' : [11, 1,   1,  24,  3],  #Swell Period Indicator
         'c2' : [12, 2,   1,  25,  1],  #2nd Country Code
       'aqcs' : [13, 12,  0,  27,  4],  #Adaptive QC Flags
         'nd' : [14, 1,   1,  39,  1],  #Night/Day Flag
       'trms' : [15, 6,   0,  40,  4],  #Trimming Flags (sf,af,uf,vf,pf,rf)
       'nqcs' : [16, 14,  0,  46,  4],  #NCDC-QC Flags (znc,wnc,bnc,xnc,ync,pnc,anc,gnc,dnc,snc,cnc,enc,fnc,tnc)
        'qce' : [17, 2,   1,  60,  4],  #External Flag
         'lz' : [18, 1,   1,  62,  4],  #Landlocked Flag
        'qcz' : [19, 2,   1,  63,  4]   #Source Exclusion Flags
      }
      self.IIMMT5 = {   # atti = ' 5', attl = 94
      #          IDX SIZE PREC POS TYPE UNIT  MAX  Description
         'os' : [0,  1,   1,   4,  1],             #Obervation Source
         'op' : [1,  1,   1,   5,  1],             #Observation Platform
         'fm' : [2,  1,   0,   6,  1],             #FM Code Version
       'immv' : [3,  1,   0,   7,  1],             #IMMT Version
         'ix' : [4,  1,   1,   8,  3],             #Station/Weather Indicator
         'w2' : [5,  1,   1,   9,  0],             #2nd Past Weather
        'wmi' : [6,  1,   1,  10,  3],             #Wave Meassure Indicator
        'sd2' : [7,  2,  10,  11,  0,  "deg"],     #2nd Swell direction
        'sp2' : [8,  2,   1,  13,  0,    "s"],     #2nd Swell Period
        'sh2' : [9,  2, 0.5,  15,  0,    "m", 99], #2nd Swell Height
        'ics' : [10, 1,   1,  17,  0],             #Ice Accretion on Ship
         'es' : [11, 2,   1,  18,  0,   "cm"],     #Thickness of IS
         'rs' : [12, 1,   1,  20,  0],             #Rate of IS
        'ic1' : [13, 1,   0,  21,  0],             #Concentration of Sea Ice
        'ic2' : [14, 1,   0,  22,  3],             #Stage of Development
        'ic3' : [15, 1,   0,  23,  1],             #Ice of Land Origin
        'ic4' : [16, 1,   0,  24,  0],             #True Bearing Ice Edge
        'ic5' : [17, 1,   0,  25,  0],             #Ice situation/Trend
         'ir' : [18, 1,   1,  26,  3],             #Precipitation Data Indicator
        'rrr' : [19, 3,   1,  27,  0,   "mm"],     #Amount of Precipitation
         'tr' : [20, 1,   1,  30,  3],             #Duration of RRR
         'nu' : [21, 1,   0,  31,  1],             #National Use
        'qci' : [22, 1,   1,  32,  3],             #QC Indicator
        'qis' : [23, 20,  0,  33,  4],             #QC Indicator for Fields (qi1-qi20)
       'qi21' : [24, 1,   1,  53,  2],             #MQCS Version
        'hdg' : [25, 3,   1,  54,  0,  "deg"],     #Ship Heading
        'cog' : [26, 3,   1,  57,  0,  "deg"],     #Cource Over Ground
        'sog' : [27, 2,   1,  60,  0,   "kt"],     #Speed Over Ground
        'sll' : [28, 2,   1,  62,  0,    "m"],     #max.ht>Sum Land Ln
       'slhh' : [29, 3,   1,  64,  0,    "m"],     #Dep. Load Ln.: Sea Lev.
        'rwd' : [30, 3,   1,  67,  0,  "deg"],     #Relative Wind Direction
        'rws' : [31, 3, 0.1,  70,  0,  "m/s"],     #Relative wind speed
       'qi22' : [32, 8,   0,  73,  3],             #QC Indicator for Fields (qi22-q129)
         'rh' : [33, 4, 0.1,  81,  0,    "%"],     #Relative Humidity
        'rhi' : [34, 1,   1,  85,  3],             #Relative Humidity Indicator
       'awsi' : [35, 1,   1,  86,  3],             #AWS Indicator
      'imono' : [36, 7,   1,  87,  1],             #IMO Number
      }
      self.IMODQC = {   # atti = ' 6', attl 68
      #          IDX SIZE PREC POS TYPE UNIT   Description
       'cccc' : [0,  4,   0,   4,  1],         #Collecting Center
       'buid' : [1,  6,   0,   8,  1],         #Bulletin ID
      'fbsrc' : [2,  1,   1,  14,  1],         #feedback source
        'bmp' : [3,  5, 0.1,  15,  0,  "hPa"], #Background SLP
       'bswu' : [4,  4, 0.1,  20,  0,  "m/s"], #Background Wind U Comp.
        'swu' : [5,  4, 0.1,  24,  0,  "m/s"], #Derived Wind U Comp.
       'bswv' : [6,  4, 0.1,  28,  0,  "m/s"], #Background Wind V Comp.
        'swv' : [7,  4, 0.1,  32,  0,  "m/s"], #Derived Wind V Comp.
       'bsat' : [8,  4, 0.1,  36,  0, "degC"], #Background Air Temperature
       'bsrh' : [9,  3,   1,  40,  0,    "%"], #Background Relative Humidity
        'srh' : [10, 3,   1,  43,  0,    "%"], #Derived Relative Humidity
       'bsst' : [11, 5, .01,  46,  0, "degC"], #Background SST
        'mst' : [12, 1,   1,  51,  1],         #Model Surface Type
        'msh' : [13, 4,   1,  52,  0,    "m"], #Model Height of Land Surface
        'byr' : [14, 4,   1,  56,  1],         #Background Year
        'bmo' : [15, 2,   1,  60,  1],         #Background Month
        'bdy' : [16, 2,   1,  62,  1],         #Background Day
        'bhr' : [17, 2,   1,  64,  1],         #Background Hour
        'bfl' : [18, 2,   1,  66,  1,  "min"]  #Background Forecast Length
      }
      self.IMETAVOS = {   # atti = ' 7', attl = 58
      #          IDX SIZE PREC POS TYPE UNIT   Description
        'mds' : [0,  1,   0,   4,  1],         #metadata source
        'c1m' : [1,  2,   0,   5,  1],         #Recruiting Country
        'opm' : [2,  2,   1,   7,  1],         #Type of Ship
        'kov' : [3,  2,   0,   9,  1],         #Kind of Vessel
        'cor' : [4,  2,   0,  11,  1],         #Country of Registry
        'tob' : [5,  3,   0,  13,  1],         #Type of Barometer
        'tot' : [6,  3,   0,  16,  1],         #Type of Thermometer
        'eot' : [7,  2,   0,  19,  1],         #Exposure of Thermometer
        'lot' : [8,  2,   0,  21,  1],         #Screen Location
        'toh' : [9,  1,   0,  23,  1],         #Type of Hygrometer
        'eoh' : [10, 2,   0,  24,  1],         #Exposure of Hygrometer
        'sim' : [11, 3,   0,  26,  1],         #SST Measurement Method
        'lov' : [12, 3,   1,  29,  0,   "m"],  #Length of Vessel
        'dos' : [13, 2,   1,  32,  0,   "m"],  #Depth of SST Measusrement
        'hop' : [14, 3,   1,  34,  0,   "m"],  #Height of Visual Obs. Platform
        'hot' : [15, 3,   1,  37,  0,   "m"],  #Height of AT Sensor
        'hob' : [16, 3,   1,  40,  0,   "m"],  #Height of Barometer
        'hoa' : [17, 3,   1,  43,  0,   "m"],  #Height of Anemometer
        'smf' : [18, 5,   1,  46,  1],         #Source Metadata File
        'sme' : [19, 5,   1,  51,  1],         #Source Meta. Element
        'smv' : [20, 2,   1,  56,  1]          #Source Format Version
      }
      self.INOCN = {    # atti = ' 8', attl = 102
      #          IDX SIZE PREC     POS TYPE UNIT       Description
        'otv' : [0,  5,   0.001,    4, 0,    "degC"],  #temperature value
        'otz' : [1,  4,   0.01,     9, 0,       "m"],  #temperature depth
        'osv' : [2,  5,   0.001,   13, 0],             #salinity value
        'osz' : [3,  4,   0.01,    18, 0,       "m"],  #salinity depth
        'oov' : [4,  4,   0.01,    22, 0,    "ml/l"],  #dissolved oxygen
        'ooz' : [5,  4,   0.01,    26, 0,       "m"],  #dissolved oxygen depth
        'opv' : [6,  4,   0.01,    30, 0,    "mm/l"],  #phosphate value
        'opz' : [7,  4,   0.01,    34, 0,       "m"],  #phosphate depth
       'osiv' : [8,  5,   0.01,    38, 0,    "mm/l"],  #silicate value
       'osiz' : [9,  4,   0.01,    43, 0,       "m"],  #silicate depth
        'onv' : [10, 5,   0.01,    47, 0,    "mm/l"],  #nitrate value
        'onz' : [11, 4,   0.01,    52, 0,       "m"],  #nitrate depth
       'ophv' : [12, 3,   0.01,    56, 0],             #pH value
       'ophz' : [13, 4,   0.01,    59, 0,       "m"],  #pH depth
        'ocv' : [14, 4,   0.01,    63, 0,    "mg/l"],  #total chlorophyll value
        'ocz' : [15, 4,   0.01,    67, 0,       "m"],  #total chlorophyll depth
        'oav' : [16, 3,   0.01,    71, 0,    "me/l"],  #alkalinity value
        'oaz' : [17, 4,   0.01,    74, 0,       "m"],  #alkalinity depth
       'opcv' : [18, 4,   1,       78, 0,      "ma"],  #partial pressure of carbon dioxide value
       'opcz' : [19, 4,   0.01,    82, 0,       "m"],  #partial pressure of carbon dioxide depth
        'odv' : [20, 2,   1,       86, 0,    "mm/l"],  #dissolved inorganic carbon value
        'odz' : [21, 4,   0.01,    88, 0,       "m"],  #dissolved inorganic carbon depth
       'puid' : [22, 10,  0,       92, 0]              #provider's unique record identification
      } 
      self.IECR = {   # atti = ' 9', attl = 32
      #          IDX SIZE PREC    POS TYPE  UNIT      Description
        'cce' : [0,  1,   0,       4, 1],             #change code
        'wwe' : [1,  2,   1,       5, 0],             #present weather
         'ne' : [2,  1,   1,       7, 0],             #total cloud amount
        'nhe' : [3,  1,   1,       8, 0],             #lower cloud amount
         'he' : [4,  1,   1,       9, 0],             #lower cloud base height
        'cle' : [5,  2,   1,      10, 0],             #low cloud type
        'cme' : [6,  2,   1,      12, 0],             #middle cloud type
        'che' : [7,  1,   1,      14, 0],             #high cloud type
         'am' : [8,  3,   0.01,   15, 0,   'okta'],   #middle cloud amount
         'ah' : [9,  3,   0.01,   18, 0,   'okta'],   #high cloud amount
         'um' : [10, 1,   1,      21, 0,   'okta'],   #NOL middle amount
         'uh' : [11, 1,   1,      22, 0,   'okta'],   #NOL high amount
        'sbi' : [12, 1,   1,      23, 3],             #sky-brightness indicator
         'sa' : [13, 4,   0.01,   24, 1,    'deg'],   #solar altitude
         'ri' : [14, 4,   0.01,   28, 1]              #relative lunar illuminance
      }
      self.IREANQC = {  # atti = '95', attl = 61
      #         IDX SIZE PREC    POS  Description
       'icnr' : [0,  2,   1,       4], #input component number
        'fnr' : [1,  2,   1,       6], #field number
       'dpro' : [2,  2,   1,       8], #lead reanalysis data provider
       'dprp' : [3,  2,   1,      10], #reanalysis project short name
        'ufr' : [4,  1,   1,      12], #reanalysis usage flag
       'mfgr' : [5,  7,   1,      13], #model-collocated first guess value
      'mfgsr' : [6,  7,   1,      20], #model-collocated first guess spread
        'mar' : [7,  7,   1,      27], #model-collocated analysis value
       'masr' : [8,  7,   1,      34], #model-collocated analysis spread
        'bcr' : [9,  7,   1,      41], #bias crrected value
       'arcr' : [10, 4,   0,      48], #author reference code
        'cdr' : [11, 8,   1,      52], #creation date
       'asir' : [12, 1,   1,      60], #acess status indcator
      }
      self.IIVAD = {  # atti = '96', attl = 53
      #         IDX SIZE PREC POS  Description
       'icni' : [0,  2,   1,    4], #input component number
        'fni' : [1,  2,   1,    6], #field number
       'jvad' : [2,  1,   0,    8], #scaling factor for VAD
        'vad' : [3,  6,   1,    9], #value-added data
      'ivau1' : [4,  1,   0,   15], #type indicator for VAU1
      'jvau1' : [5,  1,   0,   16], #scaleing factor for VAU1
       'vau1' : [6,  6,   1,   17], #uncertainty of type IVAU1
      'ivau2' : [7,  1,   0,   23], #type indicator for VAU2
      'jvau2' : [8,  1,   0,   24], #scaleing factor for VAU2
       'vau2' : [9,  6,   1,   25], #uncertainty of type IVAU2
      'ivau3' : [10, 1,   0,   31], #type indicator for VAU3
      'jvau3' : [11, 1,   0,   32], #scaleing factor for VAU3
       'vau3' : [12, 6,   1,   33], #uncertainty of type IVAU3
        'vqc' : [13, 1,   1,   39], #value-added QC flag
       'arci' : [14, 4,   0,   40], #author reference code-ivad
      #48  'cdi' : [15, 3,   0,   44], #creation day number
      #48 'asii' : [16, 1,   1,   47], #access status indic.
      #53
        'cdi' : [15, 8,   0,   44], #ISO-8601, YYYYMMDD
      #53
       'asii' : [16, 1,   1,   52], #access status indic.
      }
      self.IUIDA = {   # atti = '98', attl = 15
      #          IDX SIZE PREC POS  Description
        'uid' : [0,  6,   0,    4], #unique report ID
        'rn1' : [1,  1,   0,   10], #release no.: primary
        'rn2' : [2,  1,   0,   11], #release no.: secondary
        'rn3' : [3,  1,   0,   12], #release no.: tertiary
        'rsa' : [4,  1,   1,   13], #release status indicator
        'irf' : [5,  1,   1,   14]  #intermediate reject flag
      }
      self.ISUPPL = {   # stti = '99' attl = 0  (variable lenth)
      #          IDX SIZE PREC  POS  Description
       'atte' : [0,  1,   1,    4],  #Attm Encoding
       'supd' : [1,  0,   0,    5]   #Supplemental Data
      }
      self.TABLECOUNT = 12
      self.IMMA_NAMES = ['icoreloc', 'icorereg', 'iicoads', 'iimmt5', 'imodqc', 'imetavos',
                    'inocn', 'iecr', 'ireanqc', 'iivad', 'iuida', 'isuppl']
      self.CHK_NAMES = ['iimmt5', 'imodqc', 'imetavos', 'inocn', 'iecr', 'ireanqc', 'iivad', 'isuppl']
      #
      # define IMMA sections, core + attms
      #
      self.IMMAS = {
      #                TIDX ATTI  ATTL ATTM      ATTLS  CN
         'icoreloc' : [0,   '',   45,  self.ICORELOC,   '', 'Core'],
         'icorereg' : [1,   '',   63,  self.ICOREREG,   '', 'Core'],
         'iicoads'  : [2,  ' 1',  65,  self.IICOADS,  '65', 'Icoads'],
         'iimmt5'   : [3,  ' 5',  94,  self.IIMMT5,   '94', 'Immt'],
         'imodqc'   : [4,  ' 6',  68,  self.IMODQC,   '68', 'Mod-qc'],
         'imetavos' : [5,  ' 7',  58,  self.IMETAVOS, '58', 'Meta-vos'],
         'inocn'    : [6,  ' 8',  102, self.INOCN,    '2U', 'Nocn'],
         'iecr'     : [7,  ' 9',  32,  self.IECR,     '32', 'Ecr'],
         'ireanqc'  : [8,  '95',  61,  self.IREANQC,  '61', 'Rean-qc'],
      #48   'iivad'    : [9,  '96',  48,  IIVAD,    '48', 'Ivad'],
      #53
         'iivad'    : [9,  '96',  53,  self.IIVAD,    '53', 'Ivad'],
         'iuida'    : [10, '98',  15,  self.IUIDA,    '15', 'Uida'],
         'isuppl'   : [11, '99',  0,   self.ISUPPL,   ' 0', 'Suppl']
      }
      self.UIDATTI = '98'
      self.MUNIQUE = {
         'ireanqc'  : ['arcr', 'cdr'],
         'iivad'    : ['arci', 'cdi']
      }
      self.IVADSC = 'ivaddb'
      self.CNTLSC = 'cntldb'
      self.MULTI_NAMES = []
      self.ATTI2NAME = {}
      self.ATTCPOS = self.INVENTORY = self.CURTIDX = self.CURIIDX = 0
      self.CURIUID = ''
      self.IMMA_COUNTS = []
      self.UIDIDX = 0
      self.AUTHREFS = {}
      self.NUM2NAME = {}             # cache field names from component/field numbers
      self.NAME2NUM = {}             # cache component/field numbers from field names
      self.UMATCH = {}               # unique matches, use iidx as key
      self.TINFO = {}
      self.FIELDINFO = {}            # cache the field metadata info for quick find
      self.ATTM_VARS = {}
      self.MISSING = -999999
      self.ERROR = -999999
      self.LEADUID = 0
      self.CURRN3 = -1
      self.CHKEXIST = 0
      self.UIDLENGTH = 0  # uid record len
      self.UIDOFFSET = 0  # uid value offset
      self.ATTMNAME = None      # standalone attm section name to fill
      self.DATE2TIDX = {}
      self.TBLSTATUS = {}
      # call to initialize table info when the module is loaded
      self.init_table_info()

   def init_table_info(self):


      self.IMMA_COUNTS = [0]*self.TABLECOUNT
      self.ATTCPOS = self.ICORELOC['attc'][3]
      self.UIDATTI = self.IMMAS['iuida'][1]

      for aname in self.IMMA_NAMES:
         imma = self.IMMAS[aname]
         if imma[1]: self.ATTI2NAME[imma[1]] = aname
         if aname in self.MUNIQUE: self.MULTI_NAMES.append(aname)

      return 1

   #
   # identify and return the ATTM name from a given line of standalone attm input
   #
   def identify_attm_name(self, line):

      if self.LEADUID:
         self.UIDOFFSET = 0
         self.UIDLENGTH = 6
         atti = line[6:8]
      elif re.match(r'^9815', line):
         self.UIDOFFSET = 4
         self.UIDLENGTH = 15
         atti = line[15:17]
         CURRN3 = int(line[12])
      else:
         atti = None

      if atti and atti in self.ATTI2NAME:
         self.ATTMNAME = self.ATTI2NAME[atti]
      else:
         self.ATTMNAME = None

      return self.ATTMNAME

   #
   # cache field information for given attm and variable name
   #
   def cache_field_info(self, aname, var, uidopt = 0):

      if aname not in self.IMMAS: self.pglog("{}: Unkown attm name provided to fill field {}".format(aname, var), self.LGEREX)
      imma = self.IMMAS[aname]
      attm = imma[3]
      if var not in attm: self.pglog("{}: Field name not in attm {}".format(var, aname), self.LGEREX)
      fld = attm[var]

      if uidopt: self.LEADUID = uidopt
      self.FIELDINFO = {'aname' : aname, 'atti' : imma[1], 'attl' : imma[2], 'var' : var, 'fld' : fld, 'prec' : fld[2]}

   #
   # append the individual fields and return imma records for one line input
   #
   def get_imma_records(self, cdate, line, records):

      llen = len(line)
      if llen == 0: return records

      if self.CURIUID:    # got core section already
         coreidx = 2
         offset = self.UIDLENGTH
      else:
         coreidx = 0
         offset = 0
         self.CURIIDX += 1
         pgrecs = {}

      while (llen-offset) > 3:
         if coreidx < 2:
            aname = self.IMMA_NAMES[coreidx]
            coreidx += 1 
         else:
            aname = self.ATTI2NAME[line[offset:offset+2]]
         imma = self.IMMAS[aname]
         pgrec = self.get_one_attm(imma[3], offset, line)
   #48      if aname == 'iivad': pgrec['cdi'] = PgUtil.adddate('2014-01-01', 0, 0, I36(pgrec['cdi']), 'YYYYMMDD')
         if aname not in records: records[aname] = self.initialize_attm_records(imma[3])
         if self.CURIUID:
            self.append_one_attm(cdate, imma[0], imma[3], pgrec, records[aname])
         else:
            pgrecs[aname] = pgrec

         if not imma[2]: break   # force stop for suppl attm
         offset += imma[2]

      if self.CURIUID: return records

      for aname in pgrecs:
         imma = self.IMMAS[aname]
         self.append_one_attm(cdate, imma[0], imma[3], pgrecs[aname], records[aname])

      return records

   #
   # append the individual fields and return imma records for one line of multi-attm record
   #
   def get_imma_multiple_records(self, cdate, line, records):

      llen = len(line)
      if llen == 0: return records
      uid = line[4:10]
      offset = 15
      CURRN3 = int(line[12])
      aname = self.ATTI2NAME[line[15:17]]
      imma = self.IMMAS[aname]
      if aname not in records: records[aname] = self.initialize_attm_records(imma[3])

      while (llen-offset) > 3:
         pgrec = self.get_one_attm(imma[3], offset, line)
         self.append_one_attm(cdate, imma[0], imma[3], pgrec, records[aname])
         offset += imma[2]

      return records

   #
   # read file line and fill a single field value into db
   # 
   def set_imma_field(self, line):

      llen = len(line)
      var = self.FIELDINFO['var']
      pgrec = {}

      if self.ATTMNAME:      # attm name is provided
         coreidx = 2    # skip core sections
         offset = self.UIDLENGTH
         uid = line[self.UIDOFFSET:self.UIDOFFSET+6]
         cont = 1
      else:
         coreidx = 0
         offset = 0
         uid = None
         cont = 2

      getval = 0
      while (llen-offset) > 3:
         if coreidx < 2:
            aname = self.IMMA_NAMES[coreidx]
            coreidx += 1
            if aname == self.FIELDINFO['aname']: getval = 1
         else:
            atti = line[offset:offset+2]
            if atti == self.UIDATTI:
               uid = line[offset+4:offset+10]
               cont -= 1
            if atti == self.FIELDINFO['atti']:
               getval = 1
            else:
               aname = self.ATTI2NAME[atti]

         if getval:
            fld = self.FIELDINFO['fld']
            pos = offset + fld[3]
            if fld[1] > 0:
               val = line[pos:pos+fld[1]]
            else:
               val = line[pos:]
            val = val.rstrip(val)  # remove trailing whitespaces
            if len(val) > 0:
               if fld[2] > 0:
                  cnd = "{} = {}".format(var, val)
                  pgrec[var] = int(val)
               else:
                  cnd = "{} = '{}'".format(var, val)
                  pgrec[var] = val
            getval = 0
            cont -= 1
            offset += self.FIELDINFO['attl']
         else:
            offset += self.IMMAS[aname][2]

         if cont <= 0: break

      if not pgrec: return 0

      if not uid: self.pglog("Miss UID attm: " + line, self.LGEREX)

      tname = f"{self.IVADSC}.{self.FIELDINFO['aname']}_{self.CURTIDX}"
      if self.pgget(tname, "", f"iidx = {self.CURIIDX} AND {cnd}"): return 0
      return self.pgupdt(tname, pgrec, f"iidx = {self.CURIIDX}", self.LGEREX)

   #
   # get all field values for a single attm
   #
   def get_one_attm(self, attm, offset, line):

      pgrec = {}
      for var in attm:
         fld = attm[var]
         pos = offset + fld[3]
         if fld[1] > 0:
            val = line[pos:pos+fld[1]]
         else:
            val = line[pos:]

         val = val.rstrip()   # remove trailing whitespaces
         if fld[2] > 0:
            pgrec[var] = (int(val) if val else None)
         else:
            pgrec[var] = val

      return pgrec

   #
   # Initialize dict records for specified attm table
   #
   def initialize_attm_records(self, attm):

      pgrecs = {'iidx' : [], 'date' : []}
      for var in attm: pgrecs[var] = []

      return pgrecs

   #
   #  append one attm record to the multiple attm records
   #
   def append_one_attm(self, cdate, aidx, attm, pgrec, pgrecs):

      pgrecs['iidx'].append(self.CURIIDX)
      pgrecs['date'].append(cdate)
      for var in attm: pgrecs[var].append(pgrec[var])
      self.IMMA_COUNTS[aidx] += 1  # row index for individual table

   #
   # get imma attm counts for a given line of imma record
   #
   def get_imma_counts(self, line, acnts):

      llen = len(line)
      if llen == 0: return acnts

      if self.CURIUID:
         coreidx = 2
         offset = self.UIDLENGTH
      else:
         coreidx = 0
         offset = 0
         self.CURIIDX += 1

      while (llen-offset) > 3:
         if coreidx < 2:
            aname = self.IMMA_NAMES[coreidx]
            coreidx += 1
         else:
            aname = self.ATTI2NAME[line[offset:offset+2]]
         imma = self.IMMAS[aname]
         acnts[imma[0]] += 1
         if not imma[2]: break
         offset += imma[2]

      return acnts

   #
   # get imma multiple attm countsfor a given line of multi-attm record
   #
   def get_imma_multiple_counts(self, line, acnts):

      llen = len(line)
      if llen == 0: return acnts
      offset = 15
      aname = self.ATTI2NAME[line[15:17]]
      imma = self.IMMAS[aname]

      while (llen-offset) > 3:
         acnts[imma[0]] += 1
         offset += imma[2]

      return acnts

   #
   # add multiple imma records into different tables in RDADB
   #
   def add_imma_records(self, cdate, records):

      if self.INVENTORY and self.IMMA_NAMES[0] in records:   # add counting record into inventory table
         rcnt = len(records[self.IMMA_NAMES[0]]['iidx'])
         if rcnt > 0: self.INVENTORY = self.add_inventory_record(self.INVENTORY['fname'], cdate, rcnt, self.INVENTORY)
         if self.CURTIDX < self.INVENTORY['tidx']: self.CURTIDX = self.INVENTORY['tidx']
         tidx = self.CURTIDX
      else:
         tidx = self.date2tidx(cdate)
      acnts = [0]*self.TABLECOUNT
      for i in range(self.TABLECOUNT):
         if not self.IMMA_COUNTS[i]: continue
         aname = self.IMMA_NAMES[i]
         acnts[i] = self.add_records_to_table(self.IVADSC, aname, str(tidx), records[aname], cdate)
         self.IMMA_COUNTS[i] = 0

      iuida = records['iuida'] if 'iuida' in records else None
      self.update_control_tables(cdate, acnts, iuida, tidx)

      return acnts

   #
   # read attm records for given date
   #
   def read_attm_for_date(self, aname, cdate, tidx = None):

      if not tidx:
         tidx = self.date2tidx(cdate)
         if not tidx: return None
      self.CURTIDX = tidx

      table = f"{self.IVADSC}.{aname}_{tidx}"
      if aname in self.CHK_NAMES and not self.check_table_status(table): return None
      return self.pgmget(table, "*", f"date = '{cdate}' ORDER BY iidx", self.LGEREX)

   def check_table_status(self, table):

      if table not in self.TBLSTATUS: self.TBLSTATUS[table] = True if self.pgcheck(table) else False
      return self.TBLSTATUS[table]

   #
   # read core records for given date
   #
   def read_coreloc_for_date(self, cdate, tidx = None):

      if not tidx:
         tidx = self.date2tidx(cdate)
         if not tidx: return None
      self.CURTIDX = tidx

      return self.pgmget(f"{self.IVADSC}.icoreloc_{tidx}", '*', f"date = '{cdate}' ORDER BY iidx")

   def uid2iidx_tidx(self, uid, tidx):

      uidx = uid[0:2].lower()
      suid = uid[2:6]
      table = f"{self.CNTLSC}.itidx_{uidx}"
      cond = f"suid = '{suid}' AND tidx = {tidx}"      
      pgrec = self.pgget(table, "iidx", cond, self.LGEREX)
      if not pgrec:
         self.pglog(f"{suid}-{tidx}: suid-tidx not in {table}", self.LGEREX)

      return pgrec['iidx']

   def uid2iidx_date(self, uid, date):

      uidx = uid[0:2].lower()
      suid = uid[2:6]
      table = f"{self.CNTLSC}.itidx_{uidx}"
      cond = f"suid = '{suid}' AND date = {date}"
      pgrec = self.pgget(table, "iidx", cond, self.LGEREX)
      if not pgrec:
         self.pglog(f"{suid}-{date}: suid-date not in {table}", self.LGEREX)

      return pgrec['iidx']

   def uid2iidx_rn3(self, uid, rn3):

      uidx = uid[0:2].lower()
      suid = uid[2:6]
      table = f"{self.CNTLSC}.itidx_{uidx}"
      cond = f"suid = '{suid}' AND rn3 = {rn3}"
      pgrec = self.pgget(table, "iidx", cond, self.LGEREX)
      if not pgrec:
         self.pglog(f"{suid}-{rn3}: suid-rn3 not in {table}", self.LGEREX)

      return pgrec['iidx']

   #
   # read attm record for given uid
   #
   def read_attm_for_uid(self, aname, uid, tidx):

      iidx = self.uid2iidx_tidx(uid, tidx)
      table = f"{self.IVADSC}.{aname}_{tidx}"
      return self.pgget(table, "*", f"iidx = '{iidx}'", self.LGEREX)

   #
   # read core records for given uid
   #
   def read_coreloc_for_uid(self, uid, tidx):

      iidx = self.uid2iidx_tidx(uid, tidx)
      return self.pgget(f"{self.IVADSC}.icoreloc_{tidx}", '*', f"iidx = {iidx}")

   #
   # write IMMA records to file
   #
   def write_imma_file(self, fh, corelocs):

      (acount, anames, atables, aindices) = self.get_attm_names(self.CURTIDX)
      rcnt = len(corelocs['iidx'])
      acnts = [0]*self.TABLECOUNT

      for r in range(rcnt):
         coreloc = self.onerecord(corelocs, r)
         line = self.get_attm_line(self.IMMA_NAMES[0], None, 0, coreloc)
         acnts[0] += 1
         ilines = []
         acnt = -1
         for a in range(acount):
            if anames[a] in self.MUNIQUE:
               (icnt, iline) = self.get_multiple_attm_line(anames[a], atables[a], coreloc['iidx'])
               if icnt > 0:
                  acnt += icnt    # un-comment if multiple attms are counted
                  acnts[aindices[a]] += icnt
                  ilines.append(iline)
            else:
               aline = self.get_attm_line(anames[a], atables[a], coreloc['iidx'])
               if not aline: continue
               line += aline
               if anames[a] == 'iuida' and ilines:
                  for i in len(ilines):
                     ilines[i] = aline + ilines[i]
               acnts[aindices[a]] += 1
               acnt += 1

         if acnt != coreloc['attc']: line[self.ATTCPOS] = self.B36(acnt)

         fh.write(line + "\n")               # main record
         if ilines:
            for il in ilines:
               fh.write(il + "\n")    # add standalone multiple attm line

      return acnts

   #
   # write IMMA records for given date
   #
   def write_imma_records(self, fh, cdate, tidx, dumpall):

      acnts = [0]*self.TABLECOUNT
      if not tidx:
         tidx = self.date2tidx(cdate)
         if not tidx: return None

      dcnd = f"date = '{cdate}' ORDER BY iidx"
      mtable = f"{self.IVADSC}.icoreloc_{tidx}"
      pgrecs = self.pgmget(mtable, "*", dcnd)
      if not pgrecs: return None
      acnts[0] = count = len(pgrecs['iidx'])
      minidx = pgrecs['iidx'][0]
      jcnd = "m.iidx = n.iidx AND " + dcnd
      tcnd = f"tidx = {tidx} AND attm ="
      atable = f"{self.CNTLSC}.iattm"

      lines = ['']*count
      attcs = [-2]*count
      if dumpall: ulines = ['']*count
      self.build_imma_lines(self.IMMA_NAMES[0], minidx, count, pgrecs, lines, attcs)
      atsave = pgrecs['attc']

      # dump main record
      for a in range(1, self.TABLECOUNT):
         aname = self.IMMA_NAMES[a]
         if aname in self.MUNIQUE: continue
         if self.pgget(atable, "", f"{tcnd} '{aname}'"):
            ntable = f"{self.IVADSC}.{aname}_{tidx}"
            pgrecs = self.pgmget(f"{mtable} m, {ntable} n", "n.*", jcnd)
            if not pgrecs: continue
            acnts[a] = len(pgrecs['iidx'])
            if dumpall and aname == "iuida":
               self.build_imma_lines(aname, minidx, acnts[a], pgrecs, ulines, attcs)
               for i in range(count):
                  lines[i] += ulines[i]
            else:
               self.build_imma_lines(aname, minidx, acnts[a], pgrecs, lines, attcs)

      if dumpall:   # append the multi-line attms
         for a in range(1, self.TABLECOUNT):
            aname = self.IMMA_NAMES[a]
            if self.MUNIQUE[aname] is None: continue
            if self.pgget(atable, "", f"{tcnd} '{aname}'"):
               ntable = f"{self.IVADSC}.{aname}_{tidx}"
               pgrecs = self.pgmget(f"{mtable} m, {ntable} n", "n.*", jcnd)
               if not pgrecs: continue
               acnts[a] = len(pgrecs['iidx'])
               self.append_imma_lines(aname, minidx, acnts[a], pgrecs, ulines, lines, attcs)

      for i in range(count):
         if attcs[i] != atsave[i]:
            acnt = attcs[i]
            line = lines[i]
            lines[i] = line[0:self.ATTCPOS] + self.B36(acnt) + line[self.ATTCPOS+1:]
         fh.write(lines[i] + "\n")

      return acnts

   #
   # build daily imma lines by appending each attm 
   #
   def build_imma_lines(self, aname, minidx, count, pgrecs, lines, attcs):

      imma = self.IMMAS[aname]
      attm = imma[3]

      if aname in self.ATTM_VARS:
         vars = self.ATTM_VARS[aname]
      else:
         self.ATTM_VARS[aname] = vars = self.order_attm_variables(attm)

      for i in range(count):
         pgrec = self.onerecord(pgrecs, i)
         line = ''
         for var in vars:
            vlen = attm[var][1]
            if vlen > 0:
               if pgrec[var] is None:
                  line += "{:{}}".format(' ', vlen)
               elif attm[var][2] > 0:
                  line += "{:{}}".format(pgrec[var], vlen)
               else:
                  line += "{:{}}".format(pgrec[var], vlen)
            elif pgrec[var] is not None:
               line += pgrec[var]     # append note

         idx = pgrec['iidx'] - minidx
         lines[idx] += imma[1] + imma[4] + line
         attcs[idx] += 1 

   #
   # append daily imma lines for each multi-line attm 
   #
   def append_imma_lines(self, aname, minidx, count, pgrecs, ulines, lines, attcs):

      imma = self.IMMAS[aname]
      attm = imma[3]

      if self.ATTM_VARS[aname]:
         vars = self.ATTM_VARS[aname]
      else:
         self.ATTM_VARS[aname] = vars = self.order_attm_variables(attm)

      pidx = -1
      for i in range(count):
         pgrec = self.onerecord(pgrecs, i)
         cidx = pgrec['iidx'] - minidx
         if cidx > pidx: lines[cidx] +=  "\n" + ulines[cidx]
         line = imma[1] + imma[4]
         for var in vars:
            vlen = attm[var][1]
            if pgrec[var] is None:
               line += "{:{}}".format(' ', vlen)
            elif attm[var][2] > 0:
               line += "{:{}}".format(pgrec[var], vlen)
            else:
               line += "{:{}}".format(pgrec[var], vlen)
         lines[cidx] += line
         attcs[cidx] += 1 
         pidx = cidx

   #
   # count IMMA records for given date
   #
   def count_imma_records(self, cdate, tidx, cntall):

      acnts = [0]*self.TABLECOUNT
      if not tidx:
         tidx = self.date2tidx(cdate)
         if not tidx: return None

      atable = f"{self.CNTLSC}.iattm"
      tcnd = f"tidx = {tidx}"
      dcnd = f"date = '{cdate}'"
      mtable = f"{self.IVADSC}.icoreloc_{tidx}"
      jcnd = "m.iidx = n.iidx AND " + dcnd
      acnts[0] = self.pgget(mtable, "", dcnd)
      if not acnts[0]: return None

      for i in range(1,self.TABLECOUNT):
         aname = self.IMMA_NAMES[i]
         if not cntall and aname in self.MUNIQUE: continue
         if self.pgget(atable, "", f"{tcnd} AND attm = '{aname}'"):
            ntable = f"{self.IVADSC}.{aname}_{tidx}"
            acnts[i] = self.pgget(f"{mtable} m, {ntable} n", "", jcnd)

      return acnts

   #
   # add inventory information into control db
   #
   def add_inventory_record(self, fname, cdate, count, inventory, cntopt = 0):

      didx = 0
      table = f"{self.CNTLSC}.inventory"

      if cntopt == 2:
         cnd = f"date = '{cdate}'"
         pgrec = self.pgget(table, "didx, count", cnd, self.LGEREX)
         if not pgrec: self.pglog(f"{table}: error get record for {cnd}", self.LGEREX)
         count = pgrec['count']
         didx = pgrec['didx']
         record = {}
      else:
         record = {'date' : cdate, 'fname' : fname, 'count' : count}

      if cntopt != 1:
         record['tidx'] = inventory['tidx']
         record['tcount'] = inventory['tcount'] + count
         record['miniidx'] = inventory['maxiidx'] + 1
         record['maxiidx'] = inventory['maxiidx'] + count
         if record['tcount'] > self.PGDBI['MAXICNT']:
            record['tidx'] += 1
            record['tcount'] = count

      if didx:
         cnd = f"didx = {didx}"
         if not self.pgupdt(table, record, cnd, self.LGEREX):
            self.pglog(f"{table}: error update table for {cnd}", self.LGEREX)
      else:
         didx = self.pgadd(table, record, self.LGEREX|self.AUTOID)

      record['didx'] = didx
      if cntopt == 2:
         record['count'] = count
         record['date'] = cdate

      return record

   #
   # get the attm names for the current tidx
   #
   def get_attm_names(self, tidx):

      anames = []
      atables = []
      aindices = []
      attms = {}
      acnt = 0
      cnd = f"tidx = {tidx}"
      pgrecs = self.pgmget(f"{self.CNTLSC}.iattm", "attm", cnd, self.LGEREX)
      if not pgrecs: self.pglog(f"miss iattm record for {cnd}", self.LGEREX)
      for aname in pgrecs['attm']: attms[aname] = 1

      for i in range(1, self.TABLECOUNT):
         aname = self.IMMA_NAMES[i]        
         if aname in attms:
            anames.append(aname)
            atables.append(f"{self.IVADSC}.{aname}_{tidx}")
            aindices.append(i)
            acnt += 1

      return (acnt, anames, atables, aindices)

   #
   # get the attm line for the attm name and current iidx
   #
   def get_attm_line(self, aname, atable, iidx, pgrec):

      if not pgrec: pgrec = self.pgget(atable, "*", f"iidx = {iidx}", self.LGEREX)
      return self.build_one_attm_line(aname, pgrec) if pgrec else None

   #
   # get the attm line for the multiple attms of current iidx
   #
   def get_multiple_attm_line(self, aname, atable, iidx):

      pgrecs = self.pgmget(atable, "*", f"iidx = {iidx} ORDER BY lidx", self.LGEREX)
      icnt = (len(pgrecs['lidx']) if pgrecs else 0)
      if not icnt: return (0, None)

      iline = ''
      for i in range(icnt):
         iline += self.build_one_attm_line(aname, self.onerecord(pgrecs, i))

      return (icnt, iline)

   #
   # build the string line for the attm record and current iidx
   #
   def build_one_attm_line(self, aname, pgrec):

      imma = self.IMMAS[aname]
      attm = imma[3]
      line = imma[1] + imma[4]

      if aname in self.ATTM_VARS:
         vars = self.ATTM_VARS[aname]
      else:
         self.ATTM_VARS[aname] = vars = self.order_attm_variables(attm)

      for var in vars:
         vlen = attm[var][1]
         if vlen > 0:
            if pgrec[var] is None:
               line += "{:{}}".format(' ', vlen)
            elif attm[var][2] > 0:
               line += "{:{}}".format(pgrec[var], vlen)
            else:
               line += "{:{}}".format(pgrec[var], vlen)
         elif pgrec[var] is not None:
            line += pgrec[var]     # append note

      return line

   #
   # find an existing imma record in RDADB
   #
   def find_imma_record(self, coreloc):

      cnd = "date = '{}'".format(coreloc['date'])
      if coreloc['dy'] is None:
         cnd += " AND dy IS NULL"
      if coreloc['hr'] is not None:
         cnd += " AND hr = {}".format(coreloc['hr'])
      else:
         cnd += " AND hr IS NULL"
      if coreloc['lat'] is not None:
         cnd += " AND lat = {}".format(coreloc['lat'])
      else:
         cnd += " AND lat IS NULL"
      if coreloc['lon'] is not None:
         cnd += " AND lon = {}".format(coreloc['lon'])
      else:
         cnd += " AND lon IS NULL"
      if coreloc['id'] is not None:
         cnd += " AND id = '{}'".format(coreloc['id'])
      else:
         cnd += " AND id IS NULL"

      pgrec = self.pgget("coreloc", "iidx", cnd, self.LGWNEX)

      return (pgrec['iidx'] if pgrec else 0)

   #
   # get imma date
   #
   def get_imma_date(self, line):

      if self.ATTMNAME:
         return self.get_itidx_date(line[self.UIDOFFSET:self.UIDOFFSET+6])
      else:
         return self.get_record_date(line[0:4], line[4:6], line[6:8])

   #
   # get the itidx record from given uid
   #
   def get_itidx_date(self, uid):

      if self.CURRN3 < 0: self.pglog(f"{uid}: Provide a RN3 (>= 0) to proceed", self.LGEREX)
      uidx = uid[0:2].lower()
      suid = uid[2:6]
      table = f"{self.CNTLSC}.itidx_{uidx}"
      cond = f"suid = '{suid}'"
      pgrecs = self.pgmget(table, "*", cond, self.LGEREX)
      ucnt = len(pgrecs['iidx']) if pgrecs else 0
      if ucnt == 0: return self.pglog(f"{uid}: not in table {table}, SKIP it", self.WARNLG)

      uidx = -1
      for i in range(ucnt):
         if pgrecs['rn3'][i] == self.CURRN3:
            uidx = i
            break
      if uidx == -1: return self.pglog(f"{uid}: not in table {table} for rn3({self.CURRN3}), SKIP it", self.WARNLG)

      iidx = pgrecs['iidx'][uidx]
      tidx = pgrecs['tidx'][uidx]
      if self.CHKEXIST:    # check
         table = f"{self.IVADSC}.{self.ATTMNAME}_{tidx}"
         cnd = f"iidx = {iidx}"
         if self.pgget(table, "", cnd): return None

      self.CURIUID = uid
      self.CURIIDX = iidx
      self.CURTIDX = tidx
      return pgrecs['date'][uidx]

   #
   # get record date for given year, month and day
   #
   def get_record_date(self, yr, mo, dy):

      mo = mo.strip()
      dy = dy.strip()
      if not mo: self.pglog("missing month", self.LGEREX)

      nyr = int(yr)
      nmo = int(mo)
      sym = "{}-{}".format(yr, mo)
      if dy:
         ndy = int(dy)
         if ndy < 1:
            ndy = 1
            self.pglog("{}-{}: set dy {} to 1".format(yr, mo, dy), self.LOGWRN)
      else:
         ndy = 1
         self.pglog("{}-{}: set missing dy to 1".format(yr, mo), self.LOGWRN)

      self.CURIUID = ''

      cdate = self.fmtdate(nyr, nmo, ndy)
      if ndy > 30 or nmo == 2 and ndy > 28:
         edate = self.enddate(sym+"-01", 0, 'M')
         if cdate > edate:
            cdate = edate
            self.pglog("{}: set {}-{} to {}".format(cdate, sym, dy, edate), self.LOGWRN)

      return cdate

   #
   # get the tidx from table inventory for given date
   #
   def date2tidx(self, cdate, getend = True):

      if cdate in self.DATE2TIDX: return self.DATE2TIDX[cdate]
      table = f"{self.CNTLSC}.inventory"
      pgrec = self.pgget(table, "tidx", "date = '{}'".format(cdate), self.LGEREX)
      if pgrec:
         self.DATE2TIDX[cdate] = pgrec['tidx']
         return pgrec['tidx']

      if getend:
         cnd = f"date < '{cdate}'"
         pgrec = self.pgget(table, "max(tidx) tidx", cnd, self.LGEREX)
      else:
         cnd = f"date > '{cdate}'"
         pgrec = self.pgget(table, "min(tidx) tidx", cnd, self.LGEREX)
      if pgrec:
         return pgrec['tidx']
      else:
         return 1

   #
   # get the date from table inventory for given iidx
   #
   def iidx2date(self, iidx):

      pgrec = self.pgget(f"{self.CNTLSC}.inventory", "date", f"miniidx <= {iidx} AND maxiidx >= {iidx}", self.LGEREX)
      return (pgrec['date'] if pgrec else None)

   #
   # get field name from the component number and field number
   #
   def number2name(self, cn, fn):

      key = cn * 100 + fn
      if key in self.NUM2NAME: return self.NUM2NAME[key]

      if cn > 0:
         offset = 3
         for i in range(2, self.TABLECOUNT):
            aname = self.IMMA_NAMES[i]
            if cn == int(self.IMMAS[aname][1]): break
         if i >= self.TABLECOUNT: self.pglog(f"{cn}: Cannot find Component", self.LGEREX)
      elif fn < 17:
         offset = 1
         aname = self.IMMA_NAMES[0]
      else:
         offset = 17
         aname = self.IMMA_NAMES[1]

      attm = self.IMMAS[aname][3]
      for fname in attm:
         if fn == (attm[fname][0]+offset):
            self.NUM2NAME[key] = [fname, aname]
            return self.NUM2NAME[key]

      self.pglog(f"{fn}: Cannot find field name in Component '{aname}'", self.LGEREX)

   #
   # get component number and field number from give field name
   #
   def name2number(self, fname):

      if fname in self.NAME2NUM: return self.NAME2NUM[fname]

      for i in range(self.TABLECOUNT):
         aname = self.IMMA_NAMES[i]
         attm = self.IMMAS[aname][3]
         if fname in attm:
            cn = int(self.IMMAS[aname][1]) if self.IMMAS[aname][1] else 0
            fn = attm[fname][0]
            if i == 0:
               fn += 1
            elif i == 1:
               fn += 17
            else:
               fn += 3

            self.NAME2NUM[fname] = [cn, fn, aname]
            return self.NAME2NUM[fname]

      self.pglog(fname + ": Cannot find Field Name", self.LGEREX)

   #
   # convert integers to floating values
   #
   def float_imma_record(self, record):

      for aname in self.IMMA_NAMES:
         if aname not in record: continue
         attm = self.IMMAS[aname][3]
         for key in attm:
            prec = attm[key][2]
            if prec == 1 or prec == 0: continue
            val = record[aname][key] if record[aname][key] else 0
            if not val: continue
            record[aname][key] = val * prec

      return record

   #
   # convert the floating values to integers
   #
   def integer_imma_record(self, record):

      for aname in self.IMMA_NAMES:
         if aname not in record: continue
         attm = self.IMMAS[aname][3]
         for key in attm:
            prec = attm[key][2]
            if prec == 1 or prec == 0: continue
            val = record[aname][key] if record[aname][key] else 0
            if not val: continue
            if val > 0:
               record[aname][key] = int(val/prec + 0.5)
            else:
               record[aname][key] = int(val/prec - 0.5)

      return record

   #
   # order attm fields according FN and return ordered field array
   #
   def order_attm_variables(self, attm, aname = None):

      if not attm: attm = self.IMMAS[aname][3]

      return list(attm)

   #
   # get max inventory index
   #
   def get_inventory_record(self, didx = 0, cntopt = 0):

      table = f"{self.CNTLSC}.inventory"

      if not didx:
         if cntopt == 2:
            pgrec = self.pgget(table, "min(date) mdate", "tcount = 0", self.LGEREX)
            if not (pgrec and pgrec['mdate']): self.pglog(table+": no counted-only inventory record exists", self.LGEREX)
            didx = self.get_inventory_didx(pgrec['mdate'], 1)
         elif cntopt == 0:
            pgrec = self.pgget(table, "max(didx) idx", "", self.LGEREX)
            didx = (pgrec['idx'] if pgrec else 0)
      if didx:
         cnd = "didx = {}".format(didx)
         pgrec = self.pgget(table, "*", cnd, self.LGEREX)
         if not pgrec: self.pglog("{}: error get record for {}".format(table, cnd), self.LGEREX)
      else:
         pgrec = {'date' : '', 'fname' : '', 'miniidx' : 0, 'maxiidx' : 0,
                  'didx' : 0, 'count' : 0, 'tcount' : 0, 'tidx' : 1}

      return pgrec

   #
   # get previous/later inventory didx for given date
   #
   def get_inventory_didx(self, cdate, prev):

      table = f"{self.CNTLSC}.inventory"
      fld = "didx, date"
      if prev:
         cnd = "date < '{}' ORDER BY date DECS".format(cdate)
      else:
         cnd = "date > '{}' ORDER BY date ASC".format(cdate)

      pgrec = self.pgget(table, fld, cnd, self.LGEREX)
      if not pgrec: self.pglog("{}: error get record for {}".format(table, cnd), self.LGEREX)

      return pgrec['didx']

   #
   # initialize the global indices
   #
   def init_current_indices(self, leaduid = 0, chkexist = 0, rn3 = 0):

      # leading info for iuida
      self.UIDIDX = self.IMMAS['iuida'][0]
      self.CURIIDX = 0
      self.CURTIDX = 1
      self.CURIUID = ''
      self.AUTHREFS = {}
      self.LEADUID = leaduid
      self.CHKEXIST = chkexist
      self.CURRN3 = rn3

   #
   # initialize indices for givn date
   #
   def init_indices_for_date(self, cdate, fname):

      if fname:
         if not self.INVENTORY: self.INVENTORY = self.get_inventory_record()
         self.INVENTORY['fname'] = fname
         self.CURIIDX = self.INVENTORY['maxiidx']
         self.CURTIDX = self.INVENTORY['tidx']
      else:
         pgrec = self.pgget(f"{self.CNTLSC}.inventory", "*", "date = '{}'".format(cdate), self.LGEREX)
         if not pgrec: self.pglog("{}: give date not in inventory yet".format(cdate), self.LGEREX)
         if self.CURIIDX < pgrec['miniidx']:
            self.CURIIDX = pgrec['miniidx'] - 1
            self.CURTIDX = pgrec['tidx'] - 1

   #
   # update or add control tables
   #
   def update_control_tables(self, cdate, acnts, iuida, tidx = 0):

      if not tidx: tidx = self.date2tidx(cdate)

      if iuida and acnts[0]:
         records = {}
         for i in range(acnts[self.UIDIDX]):
            auid = iuida['uid'][i][0:2].lower()
            if auid not in records:
               records[auid] = {'iidx' : [], 'suid' : [], 'rn3' : [], 'date' : [], 'tidx' : []}
            records[auid]['suid'].append(iuida['uid'][i][2:6])
            records[auid]['rn3'].append(iuida['rn3'][i])
            records[auid]['date'].append(cdate)
            records[auid]['tidx'].append(tidx)
            records[auid]['iidx'].append(iuida['iidx'][i])

         for auid in records:
            self.add_records_to_table(self.CNTLSC, 'itidx', auid, records[auid], cdate)

      tname = f"{self.CNTLSC}.iattm"
      dname = tname + "_daily"
      for i in range(self.TABLECOUNT):
         if not acnts[i]: continue
         aname = self.IMMA_NAMES[i]
         cnd = "attm = '{}' AND tidx = {}".format(aname, tidx)
         pgrec = self.pgget(tname, "aidx, count", cnd, self.LGWNEX)
         if pgrec:
            record = {'count' : (pgrec['count'] + acnts[i])}
            self.pgupdt(tname, record, "aidx = {}".format(pgrec['aidx']), self.LGWNEX)
         else:
            record = {'tidx' : tidx, 'attm' : aname, 'count' : acnts[i]}
            self.pgadd(tname, record, self.LGWNEX)

         cnd = "attm = '{}' AND date = '{}'".format(aname, cdate)
         pgrec = self.pgget(dname, "aidx, count", cnd, self.LGWNEX)
         if pgrec:
            record = {'count' : (pgrec['count'] + acnts[i])}
            self.pgupdt(dname, record, "aidx = {}".format(pgrec['aidx']), self.LGWNEX)
         else:
            record = {'date' : cdate, 'tidx' : tidx, 'attm' : aname, 'count' : acnts[i]}
            self.pgadd(dname, record, self.LGWNEX)

   #
   # add records to a table
   #
   def add_records_to_table(self, scname, tname, suffix, records, cdate):

      table =  f"{scname}.{tname}_{suffix}"
      if not self.check_table_status(table):
         pgcmd = self.get_pgddl_command(tname = tname, suf = suffix, scname = scname)
         if self.pgsystem(pgcmd, self.LGWNEX): self.TBLSTATUS[table] = True

      cnt = self.pgmadd(table, records, self.LGEREX)
      s = 's' if cnt > 1 else ''
      self.pglog("{}: {} records added to {}".format(cdate, cnt, table), self.LOGWRN)

      return cnt

   #
   # match imma records for given time/space, and matching variables if provided
   #
   # TODO: need more work (avoid of itable)
   #
   # return maching count
   #
   def match_imma_records(self, cdate, t1, t2, w, e, s, n, vt):

      if cdate in self.TINFO:
         tinfo = self.TINFO[cdate]
         if not tinfo: return 0
      else:
         tinfo = self.pgget(f"{self.CNTLSC}.itable", "*", "bdate <= '{}' AND edate >= '{}'".format(cdate, cdate), self.LGWNEX)
         if not tinfo:
            self.TINFO[cdate] = 0
            return 0

      # match time/latitude
      mrecs = self.pgmget(f"{self.IVADSC}.icoreloc_{tinfo['tidx']}", "*",
                     "date = '{}' AND hr BETWEEN {} AND {} AND lat BETWEEN {} AND {}".format(cdate, t1, t2, s, n), self.LGWNEX)
      if not mrecs: return 0  # no match

      cnt = len(mrecs['iidx'])
      # match longitude, and/or variables
      m = 0
      for i in range(cnt):
         mrec = self.onerecord(mrecs, i)
         if w < e:
            if mrec['lon'] < w or mrec['lon'] > e: continue
         else:
            if mrec['lon'] > e and mrec['lon'] < w: continue

         if not vt or self.match_imma_vars(tinfo, mrec, vt):
            iidx = mrec['iidx']
            if iidx not in self.UMATCH: self.UMATCH[iidx] = 1
            m += 1

      return m

   #
   # return 1 if a value is found for any given variable 0 otherwise
   #
   # TODO: need more work
   #
   def match_imma_vars(self, tinfo, mrec, vt):

      mrecs = {}
      mrecs['icoreloc'] = mrec
      iidx = mrec['iidx']
      tidx = tinfo['tidx']
      for v in vt:
         name = vt[v]
         if name not in mrecs:
            if name in tinfo:
               mrecs[name] = self.pgget(f"{self.IVADSC}.{name}_{tidx}", "*", f"iidx = {iidx}")
               if not mrecs[name]: mrecs[name] = 0
            else:
               mrecs[name] = 0

         if mrecs[name] and mrecs[name][v] is not None: return 1   # found value for variable

      return 0

   #
   # distant in km to degree in 0.01deg
   #
   def distant2degree(self, la, lo, d, b):

      P = 3.14159265
      R = 6371

      la *= P/18000
      lo *= P/18000
      b *= P/18000

      lat = int(18000 * math.asin(math.sin(la)*math.cos(d/R) + math.cos(la)*math.sin(d/R)*math.cos(b))/P + 0.5)
      lon = int(18000 * (lo + math.atan2(math.sin(b)*math.sin(d/R)*math.cos(la), math.cos(d/R) - math.sin(la)*math.sin(la)))/P + 0.5)

      return (lat, lon)

   # integer to 36-based string
   def B36(self, I36):

      STR36 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
      B36 = STR36[I36%36]
      while I36 >= 36:
         I36 = int(I36/36)
         B36 = STR36[I36%36] + B36

      return B36

   # 36-based string to integer
   def I36(self, B36):

      STR36 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
      I36 = 0
      for ch in B36:
         I36 = I36*36 + int(STR36.find(ch))

      return I36

   #
   # convert from trimqc2.f:01C by Steve Worley
   # modified for trinqc2.f01D to trim on RH
   #
   def TRIMQC2(self, record, options = None):

      values = {}
      values['sst'] = record['icorereg']['sst']
      values['at']  = record['icorereg']['at']
      values['d']   = record['icorereg']['d']
      values['w']   = record['icorereg']['w']
      values['slp'] = record['icorereg']['slp']
      values['wbt'] = record['icorereg']['wbt']
      values['dpt'] = record['icorereg']['dpt']
      values['rh']  = record['iimmt5']['rh'] if 'iimmt5' in record and record['iimmt5'] else None 

      # default to enhenced trimming
      if not options: options = {'OPDN' : 0, 'OPPT' : 1, 'OPSE' : 0, 'OPCQ' : 0, 'OPTF' : 2, 'OP11' : 1}

      # GET TRIMMING AND OTHER QUALITY CONTROL FLAGS
      TRFLG = self.GETTRF(record)
      flags = self.TRIMQC0(record['icoreloc']['yr'], record['iicoads']['dck'], record['iicoads']['sid'],
                      record['iicoads']['pt'], record['iicoads']['dups'], TRFLG, options)

      if flags['ZZQF'] == 1: return None    # RECORD REJECTED

      if flags['SZQF'] == 1: values['sst'] = None   # SST FLAG AND QC APPLICATION
      if flags['AZQF'] == 1: values['at'] = None    # AT FLAG AND QC APPLICATION
      if flags['WZQF'] == 1: values['d'] = values['w'] = None   # WIND, D AND W FLAG AND QC APPLICATION
      if flags['PZQF'] == 1: values['slp'] = None    # SLP FLAG AND QC APPLICATION
      if flags['RZQF'] == 1: values['rh'] = values['wbt'] = values['dpt'] = None  # WBT AND DPT FLAG AND QC APPLICATION

      return values

   #
   # converted from Fortran code trimqc0.f:01D by Sandy Lubker
   #
   def TRIMQC0(self, YR, DCK, SID, PT, DS, TRFLG, options):

      flags = {'ZZQF' : 1}   # INITIAL REPORT REJECTION

      # CHECK IF TRIMMING FLAGS MISSING
      if TRFLG[0] == 0:
         self.pglog('TRIMMING FLAGS MISSING', self.LGEREX)
         return flags

      # CHECK RANGES OF OPTIONS
      if options['OPDN'] < 0 or options['OPDN'] > 2:
         self.pglog("OPDN={}".format(options['OPDN']), self.LGEREX)
      if options['OPPT'] < 0 or options['OPPT'] > 1:
         self.pglog("OPPT={}".format(options['OPPT']), self.LGEREX)
      if options['OPSE'] < 0 or options['OPSE'] > 1:
         self.pglog("OPSE={}".format(options['OPSE']), self.LGEREX)
      if options['OPCQ'] < 0 or options['OPCQ'] > 1:
         self.pglog("OPCQ={}".format(options['OPCQ']), self.LGEREX)
      if options['OPTF'] < 0 or options['OPTF'] > 3:
         self.pglog("OPTF={}".format(options['OPTF']), self.LGEREX)
      if options['OP11'] < 0 or options['OP11'] > 1:
         self.pglog("OP11={}".format(options['OP11']), self.LGEREX)

      B2 = TRFLG[0]
      ND = TRFLG[1]
      SF = TRFLG[2]
      AF = TRFLG[3]
      UF = TRFLG[4]
      VF = TRFLG[5]
      PF = TRFLG[6]
      RF = TRFLG[7]
      ZQ = TRFLG[8]
      SQ = TRFLG[9]
      AQ = TRFLG[10]
      WQ = TRFLG[11]
      PQ = TRFLG[12]
      RQ = TRFLG[13]
      XQ = TRFLG[14]
      CQ = TRFLG[15]
      EQ = TRFLG[16]
      LZ = TRFLG[17]
      SZ = TRFLG[18]
      AZ = TRFLG[19]
      WZ = TRFLG[20]
      PZ = TRFLG[21]
      RZ = TRFLG[22]

      if PT is None: PT = -1
      if options['OPDN'] == 1:
         if ND == 2: return flags
      elif options['OPDN'] == 2:
         if ND == 1: return flags
      if DS > 2 and (YR >= 1950 or DS != 6): return flags
      if LZ == 1: return flags
      if (ZQ == 1 or ZQ == 3) and YR >= 1950: return flags
      if YR >= 1980:
         if SID == 25 and YR > 1984: return flags
         if SID == 30 and YR > 1984: return flags
         if SID == 33 and YR < 1986: return flags
         if options['OPPT'] == 0:
            if not (PT  == 2 or PT == 5 or PT == -1 and DCK == 888): return flags
            if SID == 70 or SID == 71: return flags
         elif options['OPPT'] == 0:
            if PT > 5: return flags
            if SID == 70 or SID == 71: return flags

      # REMOVE ELEMENT REJECTION
      flags['ZZQF'] = flags['SZQF'] = flags['AZQF'] = flags['WZQF'] = flags['PZQF'] = flags['RZQF'] = 0

      # SOURCE EXCLUSION FLAGS
      if YR < 1980 or (PT != 13 and PT != 14 and PT != 16):
         if options['OPSE'] == 0:
            if SZ == 1: flags['SZQF'] = 1
            if AZ == 1: flags['AZQF'] = 1
            if WZ == 1: flags['WZQF'] = 1
            if YR >= 1980:
               if SID == 70 or SID == 71: flags['WZQF'] = 1
            if PZ == 1: flags['PZQF'] = 1
            if RZ == 1: flags['RZQF'] = 1

      # COMPOSITE QC FLAGS
      if options['OPCQ'] == 0:
         if SQ > 0: flags['SZQF'] = 1
         if AQ > 0: flags['AZQF'] = 1
         if WQ > 0: flags['WZQF'] = 1
         if PQ > 0: flags['PZQF'] = 1
         if RQ > 0: flags['RZQF'] = 1

      # TRIMMING FLAGS
      if options['OPTF'] < 3:
         if SF > (options['OPTF']*2+1):
            if options['OP11'] == 0 or SF != 11: flags['SZQF'] = 1
         if AF > (options['OPTF']*2+1): flags['AZQF'] = 1
         if UF > (options['OPTF']*2+1) or VF > (options['OPTF']*2+1): flags['WZQF'] = 1
         if PF > (options['OPTF']*2+1):
            if options['OP11'] == 0 or PF != 11: flags['PZQF'] = 1
         if RF > (options['OPTF']*2+1): flags['RZQF'] = 1
      elif options['OPTF'] == 3:
         if SF > 12: flags['SZQF'] = 1
         if AF > 12: flags['AZQF'] = 1
         if UF > 12 or VF > 12: flags['WZQF'] = 1
         if PF > 12: flags['PZQF'] = 1
         if RF > 12: flags['RZQF'] = 1

      return flags

   #
   # get trim flags
   #
   def GETTRF(self, record):

      (ZNC,WNC,BNC,XNC,YNC,PNC,ANC,GNC,DNC,SNC,CNC,ENC,FNC,TNC) = (0,1,2,3,4,5,6,7,8,9,10,11,12,13)
      (SF,AF,UF,VF,PF,RF) = (0,1,2,3,4,5)

      QCFLG = [None]*14
      cstr = record['iicoads']['nqcs']
      if cstr:
         i = 0
         for c in cstr: 
            if c != ' ': QCFLG[i] = self.I36(c)
            i += 1

      TRIMS = [None]*6
      cstr = record['iicoads']['trms']
      if cstr:
         i = 0
         for c in cstr: 
            if c != ' ': TRIMS[i] = self.I36(c)
            i += 1

      TRFLG = [0]*23
      if record['icoreloc']['lat'] is not None and record['icoreloc']['lon'] is not None and record['iicoads']['b10'] is not None:
         TRFLG[0] = self.B2QXY(self.QB10(record['iicoads']['b10']),record['icoreloc']['lon'],record['icoreloc']['lat'])
      if record['iicoads']['nd'] is not None: TRFLG[1] = record['iicoads']['nd']
      if TRIMS[SF] is not None:
         TRFLG[2] = TRIMS[SF]
         TRFLG[3] = TRIMS[AF]
         TRFLG[4] = TRIMS[UF]
         TRFLG[5] = TRIMS[VF]
         TRFLG[6] = TRIMS[PF]
         TRFLG[7] = TRIMS[RF]

      if QCFLG[ZNC]:
         if QCFLG[ZNC] >= 7 and QCFLG[ZNC] != 10: TRFLG[8] = 1
         if QCFLG[SNC] >= 8 and QCFLG[SNC] != 10: TRFLG[9] = 1
         if QCFLG[ANC] >= 8 and QCFLG[ANC] != 10: TRFLG[10] = 1
         d = record['icorereg']['d']
         w = record['icorereg']['w']
         if d != None and w != None and d >= 1 and d <= 360 and w == 0 and QCFLG[WNC] == 7: TRFLG[11] = 1
         if QCFLG[PNC] >= 8 and QCFLG[PNC] != 10: TRFLG[12] = 1
         if QCFLG[GNC] >= 8 and QCFLG[GNC] != 10 or QCFLG[DNC] >= 8 and QCFLG[DNC] != 10: TRFLG[13] = 1
         if QCFLG[XNC] != 10:
            if QCFLG[XNC] >= 7:
               TRFLG[14] = 3
            elif QCFLG[XNC] >= 4:
               TRFLG[14] = 2
            elif QCFLG[XNC] >= 2:
               TRFLG[14] = 1
         if QCFLG[CNC] != 10:
            if QCFLG[CNC] >= 7:
               TRFLG[15] = 3
            elif QCFLG[CNC] >= 4:
               TRFLG[15] = 2
            elif QCFLG[CNC] >= 2:
               TRFLG[15] = 1
         if QCFLG[ENC] != 10:
            if QCFLG[ENC] >= 7:
               TRFLG[16] = 3
            elif QCFLG[ENC] >= 4:
               TRFLG[16] = 2
            elif QCFLG[ENC] >= 2:
               TRFLG[16] = 1

      QC = record['iicoads']['qce']
      if QC:
         for i in range(13, 7, -1):
            TRFLG[i] += 2*(QC%2)
            QC >>= 1

      if record['iicoads']['lz'] != None: TRFLG[17] = record['iicoads']['lz']

      QC = record['iicoads']['qcz']
      if QC:
         for i in range(22, 17, -1):
            TRFLG[i] += 2*(QC%2)
            QC >>= 1

      return TRFLG

   #
   #  B10 to Q value
   #
   def QB10(self, B10):

      if B10 < 1 or B10 > 648:
         return -1
      else:
         return 2 + (int((B10-1)/324))*2 - int(((B10-1+3)%36)/18)

   #
   # Q, X and Y to B2 values 
   #
   def B2QXY(self, Q, X, Y):

      YY = (-Y) if Y < 0 else Y

      if Q < 1 or Q > 4 or X < 0 or X > 35999 or YY > 9000: return 0

      if YY < 9000:
         if (Q%2) == 0:
            C = int(X/200)
            if C > 89: C = 89
         else:
            C = int(((36000-X)%36000)/200)
            if C > 89: C = 89
            C = 179-C

         if int(Q/3) == 0:
             R = 89-int((9000+Y)/200)
         else:
             R = int((9000-Y)/200)

         B2 = 2+R*180+C
      elif Y == 9000:
         B2 = 1
      else:
         B2 = 16202

      return B2

   #
   # wind speed/directory to component U and V
   #
   def wind2uv(self, w, d):

      u = v = None

      if w == 0 or d == 361:
         u = v = 0
      elif d > 0 and d < 361:
         d = numpy.deg2rad(d + 180)
         u = w * math.cos(d)
         v = w * math.sin(d)

      return (u, v)
