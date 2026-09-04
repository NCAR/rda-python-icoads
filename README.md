# rda_python_icoads

RDA Python package to manage RDA ICOADS datasets.

## Prerequisite

To dynamically generate a PDF readme fitting for each data subset, the Linux
commandline utility `wkhtmltopdf` must be installed.  See
<https://wkhtmltopdf.org/index.html> for download and install instructions.

## Programs

The package installs the following command-line utilities, all running as the
current user:

- `imma1_subset` — generate IMMA1-format ICOADS subset deliveries
- `msg3_subset` — generate MSG-format ICOADS R3 subsets
- `msg_download` — download MSG ICOADS source files
- `checkicoads` — check ICOADS archive integrity
- `cleanicoads` — clean up stale ICOADS files
- `counticoads`, `countattm`, `countattmvar`, `countsst` — record/attribute counters
- `fillicoads`, `fillinventory`, `fillitable`, `fillmonth` — populate ICOADS DB tables
- `fixiidx` — fix ICOADS indices
- `maxsst` — compute maximum SST values
- `writeicoads` — write ICOADS records

Run any program with no arguments to print its usage details.

## Environment setup

Create a Python environment first; package installs in the next section run
inside whichever environment you activate here.

### Option A — Python venv (DECS machines)

```bash
python3 -m venv $ENVHOME          # e.g. /glade/u/home/gdexdata/gdexmsenv
source $ENVHOME/bin/activate
```

### Option B — Conda (DAV/Casper)

```bash
conda create --prefix $ENVHOME python=3.12   # e.g. /glade/work/gdexdata/conda-envs/pg-gdex
conda activate $ENVHOME
```

## Installing rda-python-icoads

Pick whichever install mode fits your workflow.  All variants pull in the
transitive dependency (`rda_python_common`) automatically.

For local development, clone this repo alongside your project and install it
in editable mode so that changes are picked up without re-installing:

```bash
git clone https://github.com/NCAR/rda-python-icoads.git
cd rda-python-icoads
pip install -e .
```

To test a specific branch (e.g. an in-progress feature or fix branch), pass
`-b/--branch` to `git clone`:

```bash
git clone -b <branch-name> https://github.com/NCAR/rda-python-icoads.git
cd rda-python-icoads
pip install -e .
```

For a regular (non-editable) install from a checkout:

```bash
pip install /path/to/rda-python-icoads
```

For a production install on a system that uses the published distribution:

```bash
pip install rda_python_icoads
```
