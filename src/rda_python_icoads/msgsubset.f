!------------------------------------------------------------------------------
!
!     Title : msgsubset.f
!    Author : Zaihua Ji,  zji@ucar.edu
!      Date : 11/16/2010
!             2025-02-28 transferred to package rda_python_icoads from
!             subset.f in https://github.com/NCAR/rda-icoads.git
!   Purpose : Fortran program Subsetting ICOADS MSG data
!
!    Github : https://github.com/NCAR/rda-python-icoads.git
!
! Instruction:
!    after python -m pip install rda_python_icoads
!    cd $ENVHOME/bin/
!    gfortran -o msgsubset $ENVHOME/lib/python3.n*/site-packages/rda_python_icoads/msgsubset.f
!
!           *: python 3 release number, for example n = 10 in Python 3.10.12
!    $ENVHOME: /glade/u/home/rdadata/rdamsenv (venv) on DECS machines, and
!              /glade/work/rdadata/conda-envs/pg-rda (conda) on DAV;
!------------------------------------------------------------------------------
      PROGRAM SUBSET
      IMPLICIT INTEGER(A-E,G-Z)
!
      CHARACTER*15 PROGID
      DATA PROGID/'SUBSET.MSG.01B'/
C     Read and extract MSG data within specified time and region
c     on LINUX machine, compile it as 'gfortran -o subset subset.f'
C
      DATA UNIT/1/,FMISS/-9999./
C
      CHARACTER RPT*64
C
      CHARACTER FORMAT*640
      PARAMETER(NUMBER=49, iout=20)

      parameter (iomax=500000) !maximum number of records in an output file

      COMMON /MSG1/FUNITS(NUMBER,3:9),FBASE(NUMBER,3:9),BITS(NUMBER)
     +,OFFSET(NUMBER),FORMAT(3:9),RPTID,INDXCK
C
      DIMENSION CODED(NUMBER),FTRUE(NUMBER)
      PARAMETER(S1=1,S3=2,S5=3,M=4,N=5,S=6,D=7,H=8,X=9,Y=10)
      REAL YEAR,MONTH,BSZ,BLO,BLA,PID1,PID2,GRP,CK
      COMMON YEAR,MONTH,BSZ,BLO,BLA,PID1,PID2,GRP,CK,FTRUE2(4,Y)
      EQUIVALENCE(FTRUE,YEAR)
C
      CHARACTER*4 type, vname
      character*120 ierror,formato,header,colhead,kname
      integer index(number),group,nstat,idstr,idend,nfile,jfile
      integer nrecin, nrecout, inlen, outlen, vlen, lennam, resol
      real alatt,alatb,alonl,alonr,alat,alon,xlat,xlon
      character*80 indir, infile, outdir, outfile

c     read control data
      read(5,'(a)')header
      read(5,'(a)')colhead
      read(5,*)group
      read(5,*)nstat
      read(5,*)(index(i),i=1,nstat)
      read(5,*)ichkmis
      read(5,'(a)')formato
      read(5,*)alatb,alatt,alonl,alonr,idstr,idend
      read(5,'(i1)')resol
      read(5,'(a3)')type
      read(5,'(a2)')vname
      vlen = lentrm(vname)
      read(5, '(a)') indir
      inlen = lentrm(indir)   ! input directory string length
      read(5, '(a)') outdir
      outlen = lentrm(outdir) ! output directory string length
      read(5, *) nfile  ! number of input msg data files
C
C final check of latitudes/longitudes, added by Hua, 05/18/04
C
      write(*,5)header(:lentrm(header)),group,nstat,ichkmis,
     *          formato(:lentrm(formato)),resol,type,vname(:vlen),
     *          alatb,alatt,alonl,alonr,idstr,idend,
     *          indir(:inlen),outdir(:outlen),nfile
 5    format(' Control data:'/,
     *        ' comment header   :',a/,
     *        ' group number     :',i6/,
     *        ' num. stats       :',i6/,
     *        ' missing data chk :',i6/,
     *        ' output format    :',a/,
     *        ' data resolution  :',i1/,
     *        ' statistic type   :',a3/,
     *        ' Variable Name    :',a/,
     *        ' latitude limits  :',2f8.2/,
     *        ' longitude limits :',2f8.2/,
     *        ' date limits      :',2i8/,
     *        ' Data Directory   :',a/,
     *        ' Output Diretory  :',a/,
     *        ' num. msg files   :',i5/)

      print*,' array index numbers for the variables :'
      write(*,'(20i3)')(index(i),i=1,nstat)

      nrecout = 0
      nrecin = 0
      jfile = 0  !output file counter
      iorec = 0

  50  continue
      if(nfile .le. 0) goto 950 ! all input files are processed
      nfile = nfile - 1
c
c get input file name and open it for read
c
      read(5, '(a)') infile
      lennam=lentrm(infile)
      print *, "Reading MSG file: " // infile(:lennam)
      if(nrecin .gt. 1)  then
         print *, "Records In:", nrecin, " & Out:", nrecout
      endif
      print *, "Number of MSG Files Left:", nfile

C     OPEN TO READ BINARY DATA measures RECL in BYTES!!!!!
      OPEN(UNIT,FORM='UNFORMATTED',ACCESS='DIRECT',RECL=LEN(RPT)
     +,STATUS='OLD',file=indir(:inlen)//infile(:lennam))

C     INITIALIZE NUMBER OF RECORDS READ
      NREC=1

C READ REPORT (MACHINE-DEPENDENT MODIFICATIONS MAY BE NEEDED)
 100  READ(UNIT,REC=NREC,IOSTAT=EOF)RPT
C EOF OF ZERO INDICATES A SUCCESSFUL READ
      IF(EOF.NE.0) GOTO 50
C INCREMENT NUMBER OF RECORDS READ
      NREC=NREC+1
      nrecin = nrecin + 1
C
C UNPACK REPORT AND CONVERT CODED TO TRUE VALUES
      GROUP=ICHAR(RPT(8:8))/16
      CALL GETRPT(RPT,CODED,FTRUE,FMISS
     +,FUNITS(1,GROUP),FBASE(1,GROUP),BITS,OFFSET,NUMBER,RPTID,INDXCK)

c     check for missing data based on key variable
      if(ftrue(ichkmis).eq.-9999.0)go to 100

c     combine yr/mn into one integer for quick comparison
      iyear = nint(ftrue(1))
      imonth = nint(ftrue(2))
      idate = iyear*100 + imonth
      ibsz = nint(ftrue(3))
      ipid2 = nint(ftrue(7))
      if(ftrue(7).eq.-9999.0)ipid2 = -9  !reset for missing PID

c     do time window check
      if(idate .lt. idstr .or. idate .gt. idend) goto 100

c     get latitude and longitude for region checking
      alat = ftrue(5)
      alon = ftrue(4)
      if(alon .ge. 360.0) then
         alon = alon - 360.0 ! just in case
      elseif(alon .lt. 0.0) then
         alon = alon + 360.0 ! in case it between -179.99 and -0.01
      endif

c     do the area window criteria tests

      if(alat .lt. alatb .or. alat .ge. alatt) goto 100

      if(alonl .lt. alonr) then
        if(alon .lt. alonl .or. alon .ge. alonr) goto 100
      else
        if(alon .lt. alonl .and. alon .ge. alonr) goto 100
      endif
c
c check file size, close it if it gets too big
c
      if(iorec .gt. iomax) then
         close(iout)
         iorec = 0
      endif
c
c open a new file for output
c
      if(iorec .eq. 0) then
         jfile = jfile + 1
         write(outfile,
     +      "('MSG',i1,'.', a, '.', a3, '.', i6, '.', i6, '_')")
     +      resol,vname(:vlen), type, idstr, idend
         lennam = lentrm(outfile)
         if(jfile .le. 9) then
            write(outfile(lentrm(outfile)+1:), '(i1)') jfile
         elseif(jfile .le. 99) then
            write(outfile(lentrm(outfile)+1:), '(i2)') jfile
         else
            write(outfile(lentrm(outfile)+1:), '(i3)') jfile
         endif
         lennam = lentrm(outfile)
         print *, "Open file for Output:",
     +        outdir(:outlen)//outfile(:lennam)
         open(iout, file=outdir(:outlen)//outfile(:lennam),
     +        form='formatted', status='new')
c        write in the comment header field column headers
         lennam = lentrm(header)
         write(iout,'(a)')header(:lennam)
         lennam = lentrm(colhead)
         write(iout,'(a)')colhead(:lennam)
      endif

c     write records to output file

      write(iout,formato)iyear,imonth,ibsz,alon,alat,ipid2,
     *              (ftrue(index(ii)),ii=1,nstat)
      iorec = iorec + 1
      nrecout = nrecout + 1

      if(iorec.le.5) write(*,formato)iyear,imonth,ibsz,alon,alat,ipid2,
     *                  (ftrue(index(ii)),ii=1,nstat)
      go to 100
! END OF FILE
 950  CONTINUE
      close(iout)
      write(*,"('INRECS: ', i10)") nrecin
      write(*,"('OUTRECS: ', i10)") nrecout

      stop
      end
C=============================================================================C
C WARNING:  Code beyond this point should not require any modification.       C
C=============================================================================C
C-----------------------------------------------------------------------3456789
      BLOCK DATA BDMSG1
      IMPLICIT INTEGER(A-E,G-Z)
C
      CHARACTER FORMAT*640
      PARAMETER(NUMBER=49)
      COMMON /MSG1/FUNITS(NUMBER,3:9),FBASE(NUMBER,3:9),BITS(NUMBER)
     +,OFFSET(NUMBER),FORMAT(3:9),RPTID,INDXCK
C
      DATA (FUNITS(I,3),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.01 ,.01 ,.01 ,.1
     3 ,.01 ,.01 ,.01 ,.1
     5 ,.01 ,.01 ,.01 ,.1
     M ,.01 ,.01 ,.01 ,.1
     N ,1. ,1. ,1. ,1.
     S ,.01 ,.01 ,.01 ,.1
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,4),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.01 ,.01 ,.01 ,.01
     3 ,.01 ,.01 ,.01 ,.01
     5 ,.01 ,.01 ,.01 ,.01
     M ,.01 ,.01 ,.01 ,.01
     N ,1. ,1. ,1. ,1.
     S ,.01 ,.01 ,.01 ,.01
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,5),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.1 ,.1 ,.1 ,.1
     3 ,.1 ,.1 ,.1 ,.1
     5 ,.1 ,.1 ,.1 ,.1
     M ,.1 ,.1 ,.1 ,.1
     N ,1. ,1. ,1. ,1.
     S ,.1 ,.1 ,.1 ,.1
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,6),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.01 ,.1 ,.01 ,.1
     3 ,.01 ,.1 ,.01 ,.1
     5 ,.01 ,.1 ,.01 ,.1
     M ,.01 ,.1 ,.01 ,.1
     N ,1. ,1. ,1. ,1.
     S ,.01 ,.1 ,.01 ,.1
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,7),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.1 ,.1 ,.1 ,.1
     3 ,.1 ,.1 ,.1 ,.1
     5 ,.1 ,.1 ,.1 ,.1
     M ,.1 ,.1 ,.1 ,.1
     N ,1. ,1. ,1. ,1.
     S ,.1 ,.1 ,.1 ,.1
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,8),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.01 ,.01 ,.1 ,.1
     3 ,.01 ,.01 ,.1 ,.1
     5 ,.01 ,.01 ,.1 ,.1
     M ,.01 ,.01 ,.1 ,.1
     N ,1. ,1. ,1. ,1.
     S ,.01 ,.01 ,.1 ,.1
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FUNITS(I,9),I=1,NUMBER)
     +/1. ,1. ,1. ,.5 ,.5 ,1. ,1. ,1. ,1.
     1 ,.1 ,.1 ,.5 ,5.
     3 ,.1 ,.1 ,.5 ,5.
     5 ,.1 ,.1 ,.5 ,5.
     M ,.1 ,.1 ,.5 ,5.
     N ,1. ,1. ,1. ,1.
     S ,.1 ,.1 ,.5 ,5.
     D ,2. ,2. ,2. ,2.
     H ,.1 ,.1 ,.1 ,.1
     X ,.1 ,.1 ,.1 ,.1
     Y ,.1 ,.1 ,.1 ,.1/
C
      DATA (FBASE(I,3),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-501. ,-8801. ,-1. ,-1.
     3 ,-501. ,-8801. ,-1. ,-1.
     5 ,-501. ,-8801. ,-1. ,-1.
     M ,-501. ,-8801. ,-1. ,-1.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,4),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-1. ,-10221. ,-10221. ,86999.
     3 ,-1. ,-10221. ,-10221. ,86999.
     5 ,-1. ,-10221. ,-10221. ,86999.
     M ,-1. ,-10221. ,-10221. ,86999.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,5),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-1. ,-1. ,-30001. ,-30001.
     3 ,-1. ,-1. ,-30001. ,-30001.
     5 ,-1. ,-1. ,-30001. ,-30001.
     M ,-1. ,-1. ,-30001. ,-30001.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,6),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-6301. ,-10001. ,-4001. ,-10001.
     3 ,-6301. ,-10001. ,-4001. ,-10001.
     5 ,-6301. ,-10001. ,-4001. ,-10001.
     M ,-6301. ,-10001. ,-4001. ,-10001.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,7),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-20001. ,-20001. ,-10001. ,-10001.
     3 ,-20001. ,-20001. ,-10001. ,-10001.
     5 ,-20001. ,-20001. ,-10001. ,-10001.
     M ,-20001. ,-20001. ,-10001. ,-10001.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,8),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-501. ,-8801. ,-30001. ,-30001.
     3 ,-501. ,-8801. ,-30001. ,-30001.
     5 ,-501. ,-8801. ,-30001. ,-30001.
     M ,-501. ,-8801. ,-30001. ,-30001.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA (FBASE(I,9),I=1,NUMBER)
     +/1799. ,0. ,-1. ,-1. ,-181. ,-1. ,-1. ,0. ,0.
     1 ,-10001. ,-10001. ,-1. ,-1.
     3 ,-10001. ,-10001. ,-1. ,-1.
     5 ,-10001. ,-10001. ,-1. ,-1.
     M ,-10001. ,-10001. ,-1. ,-1.
     N ,0. ,0. ,0. ,0.
     S ,-1. ,-1. ,-1. ,-1.
     D ,0. ,0. ,0. ,0.
     H ,-1. ,-1. ,-1. ,-1.
     X ,-1. ,-1. ,-1. ,-1.
     Y ,-1. ,-1. ,-1. ,-1./
C
      DATA BITS
     +/8 ,4 ,3 ,10 ,9 ,3 ,3 ,4 ,4
     1 ,16 ,16 ,16 ,16
     3 ,16 ,16 ,16 ,16
     5 ,16 ,16 ,16 ,16
     M ,16 ,16 ,16 ,16
     N ,16 ,16 ,16 ,16
     S ,16 ,16 ,16 ,16
     D ,4 ,4 ,4 ,4
     H ,4 ,4 ,4 ,4
     X ,4 ,4 ,4 ,4
     Y ,4 ,4 ,4 ,4/
C
      DATA OFFSET
     +/16 ,24 ,28 ,31 ,41 ,50 ,53 ,56 ,60
     1 ,64 ,80 ,96 ,112
     3 ,128 ,144 ,160 ,176
     5 ,192 ,208 ,224 ,240
     M ,256 ,272 ,288 ,304
     N ,320 ,336 ,352 ,368
     S ,384 ,400 ,416 ,432
     D ,448 ,452 ,456 ,460
     H ,464 ,468 ,472 ,476
     X ,480 ,484 ,488 ,492
     Y ,496 ,500 ,504 ,508/
C
      DATA FORMAT(3)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' S         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' A         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' Q         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' R         ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(4)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' W         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' U         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' V         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' P         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(5)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' C         ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' R         ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' X=W*U     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' Y=W*V     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(6)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' D=S-A     ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' E=(S-A)*W ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' F=QS-Q    ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' G=(QS-Q)*W',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(7)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' I=U*A     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' J=V*A     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' K=U*Q     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' L=V*Q     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(8)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' S         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' A         ',F8.2,F8.2,F8.2,F8.2,F8.0,F8.2,F8.0,F8.1,F8.1,F8.1/
     +' X=W*U     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' Y=W*V     ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA FORMAT(9)
     +/"(/' YEAR ',F5.0,' MONTH ',F3.0,' BSZ ',F2.0,' BLO ',F5.1,' BLA '
     +,F5.1,' PID1 ',F6.0,' PID2 ',F6.0,' GRP ',F3.0,' CK ',F6.0/
     +11X,6X,'S1',6X,'S3',6X,'S5',7X,'M',7X,'N',7X,'S',7X,'D',7X,'H'
     +,7X,'X',7X,'Y'/
     +' M=(QS-Q)*U',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' N=(QS-Q)*V',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' B1=W*W*W  ',F8.1,F8.1,F8.1,F8.1,F8.0,F8.1,F8.0,F8.1,F8.1,F8.1/
     +' B2=W*W*W  ',F8.0,F8.0,F8.0,F8.0,F8.0,F8.0,F8.0,F8.1,F8.1,F8.1)
     +"/
C
      DATA RPTID/1/ ,INDXCK/9/
      END
C-----------------------------------------------------------------------3456789
      SUBROUTINE GETRPT(RPT,CODED,FTRUE,FMISS
     +,FUNITS,FBASE,BITS,OFFSET,NUMBER,RPTID,INDXCK)
C     UNPACK REPORT AND CONVERT CODED TO TRUE VALUES
C
      IMPLICIT INTEGER(A-E,G-Z)
      CHARACTER*(*) RPT
      DIMENSION CODED(*),FTRUE(*),FUNITS(*),FBASE(*),BITS(*),OFFSET(*)
C
      IF(MOD(ICHAR(RPT(2:2)),16).NE.RPTID)STOP 'RPTID ERROR'
      CALL UNPACK(RPT,CODED)
      FTRUE(INDXCK)=CODED(INDXCK)
      CODED(INDXCK)=0
      DO 190 I=1,NUMBER
        IF(I.EQ.INDXCK)GOTO 190
        IF(I.GT.NUMBER-8)FUNITS(I)=2**NINT(FTRUE(3))*.05
        IF(CODED(I).EQ.0)THEN
          FTRUE(I)=FMISS
        ELSE
          FTRUE(I)=(CODED(I)+FBASE(I))*FUNITS(I)
          CODED(INDXCK)=CODED(INDXCK)+CODED(I)
        ENDIF
  190 CONTINUE
      CODED(INDXCK)=MOD(CODED(INDXCK),2**BITS(INDXCK)-1)
      IF(FTRUE(INDXCK).NE.CODED(INDXCK))STOP 'CHECKSUM ERROR'
      END
C-----------------------------------------------------------------------3456789
      SUBROUTINE UNPACK(RPT,CODED)
C     UNPACK REPORT
C
      IMPLICIT INTEGER(A-E,G-Z)
      CHARACTER*(*) RPT
      DIMENSION CODED(*)
C
      CODED(1)=ICHAR(RPT(3:3))
      CODED(2)=ICHAR(RPT(4:4))/16
      CODED(3)=MOD(ICHAR(RPT(4:4)),16)/2
      CODED(4)=(MOD(ICHAR(RPT(4:4)),2)*256+ICHAR(RPT(5:5)))*2
     ++ICHAR(RPT(6:6))/128
      CODED(5)=MOD(ICHAR(RPT(6:6)),128)*4+ICHAR(RPT(7:7))/64
      CODED(6)=MOD(ICHAR(RPT(7:7)),64)/8
      CODED(7)=MOD(ICHAR(RPT(7:7)),8)
      CODED(8)=ICHAR(RPT(8:8))/16
      CODED(9)=MOD(ICHAR(RPT(8:8)),16)
      CODED(10)=ICHAR(RPT(9:9))*256+ICHAR(RPT(10:10))
      CODED(11)=ICHAR(RPT(11:11))*256+ICHAR(RPT(12:12))
      CODED(12)=ICHAR(RPT(13:13))*256+ICHAR(RPT(14:14))
      CODED(13)=ICHAR(RPT(15:15))*256+ICHAR(RPT(16:16))
      CODED(14)=ICHAR(RPT(17:17))*256+ICHAR(RPT(18:18))
      CODED(15)=ICHAR(RPT(19:19))*256+ICHAR(RPT(20:20))
      CODED(16)=ICHAR(RPT(21:21))*256+ICHAR(RPT(22:22))
      CODED(17)=ICHAR(RPT(23:23))*256+ICHAR(RPT(24:24))
      CODED(18)=ICHAR(RPT(25:25))*256+ICHAR(RPT(26:26))
      CODED(19)=ICHAR(RPT(27:27))*256+ICHAR(RPT(28:28))
      CODED(20)=ICHAR(RPT(29:29))*256+ICHAR(RPT(30:30))
      CODED(21)=ICHAR(RPT(31:31))*256+ICHAR(RPT(32:32))
      CODED(22)=ICHAR(RPT(33:33))*256+ICHAR(RPT(34:34))
      CODED(23)=ICHAR(RPT(35:35))*256+ICHAR(RPT(36:36))
      CODED(24)=ICHAR(RPT(37:37))*256+ICHAR(RPT(38:38))
      CODED(25)=ICHAR(RPT(39:39))*256+ICHAR(RPT(40:40))
      CODED(26)=ICHAR(RPT(41:41))*256+ICHAR(RPT(42:42))
      CODED(27)=ICHAR(RPT(43:43))*256+ICHAR(RPT(44:44))
      CODED(28)=ICHAR(RPT(45:45))*256+ICHAR(RPT(46:46))
      CODED(29)=ICHAR(RPT(47:47))*256+ICHAR(RPT(48:48))
      CODED(30)=ICHAR(RPT(49:49))*256+ICHAR(RPT(50:50))
      CODED(31)=ICHAR(RPT(51:51))*256+ICHAR(RPT(52:52))
      CODED(32)=ICHAR(RPT(53:53))*256+ICHAR(RPT(54:54))
      CODED(33)=ICHAR(RPT(55:55))*256+ICHAR(RPT(56:56))
      CODED(34)=ICHAR(RPT(57:57))/16
      CODED(35)=MOD(ICHAR(RPT(57:57)),16)
      CODED(36)=ICHAR(RPT(58:58))/16
      CODED(37)=MOD(ICHAR(RPT(58:58)),16)
      CODED(38)=ICHAR(RPT(59:59))/16
      CODED(39)=MOD(ICHAR(RPT(59:59)),16)
      CODED(40)=ICHAR(RPT(60:60))/16
      CODED(41)=MOD(ICHAR(RPT(60:60)),16)
      CODED(42)=ICHAR(RPT(61:61))/16
      CODED(43)=MOD(ICHAR(RPT(61:61)),16)
      CODED(44)=ICHAR(RPT(62:62))/16
      CODED(45)=MOD(ICHAR(RPT(62:62)),16)
      CODED(46)=ICHAR(RPT(63:63))/16
      CODED(47)=MOD(ICHAR(RPT(63:63)),16)
      CODED(48)=ICHAR(RPT(64:64))/16
      CODED(49)=MOD(ICHAR(RPT(64:64)),16)
      END
      FUNCTION LENTRM(STR)
C     LENGTH OF A STRING MINUS TRAILING BLANKS
      CHARACTER STR*(*)
      DO 190 LENTRM=LEN(STR),1,-1
        IF (STR(LENTRM:LENTRM).NE.' ') RETURN
  190 CONTINUE
      END
