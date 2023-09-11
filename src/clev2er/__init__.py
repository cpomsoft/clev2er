"""
# CLEV2ER L2 Algorithm Framework

A generic python algorithm framework, designed for (but not restricted to) Level-1b to Level-2 
processing of ESA radar altimetry mission data. Initial usage is expected for the ESA CryoSat-2 
and CRISTAL missions. The key features of the framework are dynamically loaded algorithm classes 
(from YML lists of algorithms) and in-built support for multi-processing and a consistent automated 
development and testing workflow. There are many run-time options in the chain controller 
command line tool.

The diagram below shows a simplified representation of the framework and its components.

```mermaid
graph LR;
    L1b(L1b)-->Alg1
    Alg1-->Alg2;
    Alg2-->Alg3;
    Alg3-->Alg4;
    Alg4-->AlgN;
    AlgN-->L2(L2)
    S(Shared Dict)
    S<-.->Alg1 & Alg3 & Alg4 & AlgN
    S-.->Alg2 
```
```mermaid
graph LR;
    C(Config)~~~L(Logs)~~~R{{Run Controller}}~~~LI(Alg List)-.-Ch(Chain)
```

## Main Features

* Command line chain controller tool : src/clev2er/tools/run_chain.py
* input L1b file selection (single file, multiple files or dynamic algorithm selection)
* dynamic algorithm loading from YML list(s)
  * algorithms are classes of type Algorithm with configurable .init(), .process(), .finalize() 
    functions.
  * Algorithm.init() is called before any L1b file processing.
  * Algorithm.process() is called on every L1b file,
  * Algorithm.finalize() is called after all files have been processed.
  * Each algorithm has access to: L1b Dataset, shared working dict, config dict.
  * The 'shared_dict' is used to pass algorithm outputs between algorithms in the chain.
* logging with standard warning, info, debug, error levels (+ multi-processing logging support)
* optional multi-processing built in, configurable maximum number of processes used.
* optional use of shared memory (for example for large DEMs and Masks) when using multi-processing. 
This is an optional experimental feature that must be used with great care as it can result in
memory leaks (requiring a server reboot to free) if shared memory is not correctly closed.
* algorithm timing (with MP support)
* chain timing

##Processing chains already implemented in framework:

-   CryoTEMPO Land Ice : view the algorithms: `clev2er.algorithms.cryotempo`

## Installation of the Framework

Note that the framework installation has been tested on Linux and MacOS systems. Use on
other operating systems is possible but may require additional install steps, and is not 
directly supported.

Make sure you have *git* installed on your target system.  

Clone the git public repository in to a suitable directory on your system.
This will create a directory called **/clev2er** in your current directory.

with https:  
`git clone https://github.com/cpomsoft/clev2er.git`  

or with ssh:  
`git clone git@github.com:cpomsoft/clev2er.git`  

or with the GitHub CLI:  
`gh repo clone cpomsoft/clev2er`  

## Shell Environment Setup

The following shell environment variables need to be set to support framework
operations. 

In a bash shell this might be done by adding export lines to your $HOME/.bashrc file.  

- Set the *CLEV2ER_BASE_DIR* environment variable to the root of the clev2er package.  
- Add $CLEV2ER_BASE_DIR/src to *PYTHONPATH*.   
- Add ${CLEV2ER_BASE_DIR}/src/clev2er/tools to the *PATH*.   
- Set the shell's *ulimit -n* to allow enough file descriptors to be available for
    multi-processing.

An example environment setup is shown below (the path in the first line should be
adapted for your specific directory path):

```script
export CLEV2ER_BASE_DIR=/Users/someuser/software/clev2er
export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src
export PATH=${CLEV2ER_BASE_DIR}/src/clev2er/tools:${PATH}
# for multi-processing/shared mem support set ulimit
# to make sure you have enough file descriptors available
ulimit -n 8192
```

### Environment Setup for Specific Chains

Additional environment setup maybe required for specific chains. This is not 
necessary unless you intend to use these chains.

#### cryotempo (land ice)

The following is an example of additional environment variables required by the **cryotempo**
chain. Values used are site specific.

```script
# Environment for CLEV2ER:cryotempo chain
export CPDATA_DIR=/cpdata
export CPOM_SOFTWARE_DIR=/cpnet/software/cpom_software
export FES2014B_BASE_DIR=/cpnet/mssldba_raid6/cpdata/SATS/RA/CRY/L1B/FES2014
export CATS2008A_BASE_DIR=/cpnet/mssldba_raid6/cpdata/SATS/RA/CRY/L2I/SIN/CATS_tides
export CS2_SLOPE_MODELS_DIR=/cpnet/mssldba_raid6/cpdata/RESOURCES/slope_models
export CS2_UNCERTAINTY_BASE_DIR=/cpnet/mssldba_raid6/cryo-tempo/land_ice/uncertainty
export CT_LOG_DIR=/tmp
```

## Python Requirement

python v3.10 must be installed or available before proceeding.
A recommended minimal method of installation of python 3.10 is using miniconda as 
follows (other appropriate methods may also be used):

For miniconda installation, select the **python 3.10** installer for your operating 
system from:

https://docs.conda.io/en/latest/miniconda.html

For example, for Linux, download the installer and install 
a minimal python 3.10 installation using:

```script
wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.5.2-0-Linux-x86_64.sh
chmod +x Miniconda3-py310_23.5.2-0-Linux-x86_64.sh
./Miniconda3-py310_23.5.2-0-Linux-x86_64.sh

Do you wish the installer to initialize Miniconda3
by running conda init? [yes|no] yes
```
You may need to start a new shell to refresh your environment before
checking that python 3.10 is in your path.

Check that python v3.10 is now available, by typing:

```
python -V
```

## Virtual Environment and Package Requirements

This project uses *poetry* (a dependency manager, see: https://python-poetry.org/) to manage 
package dependencies and virtual envs.

First, you need to install *poetry* on your system using instructions from
https://python-poetry.org/docs/#installation. Normally this just requires running:

`curl -sSL https://install.python-poetry.org | python3 -`

You should also then ensure that poetry is in your path, such that the command

`poetry --version`

returns the poetry version number. You may need to modify your 
PATH variable in order to achieve this.

### Install Required Python packages using Poetry

Run the following command to install python dependencies for this project
(for info, it uses settings in pyproject.toml to know what to install)

```
cd $CLEV2ER_BASE_DIR
poetry install
```


### Load the Virtual Environment

Now you are all setup to go. Whenever you want to run any CLEV2ER chains you 
must first load the virtual environment using the `poetry shell` command.

```
cd $CLEV2ER_BASE_DIR
poetry shell
```

Note that if you have the wrong version of python (not v3.10) in your path you will see
errors. You can tell poetry which version of python to use in this case using:

```
poetry env use $(which python3.10)
poetry shell
```

You should now be setup to run processing chains, etc.

## Developer Requirements

This section details additional installation requirements for developers who will develop/adapt 
new chains or algorithms.

### Install pre-commit hooks

pre-commit hooks are static code analysis scripts which are run (and must be passed) before
each git commit. For this project they include pylint, flake8, mypy, black, isort, pdocs.

To install pre-commit hooks, do the following: (note that the second line is not necessary if 
you have already loaded the virtual environment using `poetry shell`)

```
cd $CLEV2ER_BASE_DIR
poetry shell
pre-commit install
pre-commit run --all-files
```

Now, whenever you make changes to your code, it is recommended to run the following
in your current code directory.  

```pre-commit run --all-files```

This will check that your code passes all static code
tests prior to running git commit. Note that these same tests are also run when
you do a new commit, ie using `git commit -a -m "commit message"`. If the tests fail
you must correct the errors before proceeding, and then rerun the pre-commit and/or git commit.

## Run a simple chain test example

The following command will run a simple example test chain which dynamically loads
2 template algorithms and runs them on a set of CryoSat L1b files in a test data directory. 
The algorithms do not perform any actual processing as they are just template examples.
Make sure you have the virtual environment already loaded using `poetry shell` before
running this command.

`run_chain.py -n testchain -d $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles`

There should be no errors.

Note that the algorithms that are dynamically run are located in 
$CLEV2ER_BASE_DIR/src/clev2er/algorithms/testchain/testalg1.py, testalg2.py

The list of algorithms (and their order) for *testchain* are defined in 
$CLEV2ER_BASE_DIR/config/algorithm_lists/testchain.yml

Algorithm configuration settings are defined in
$CLEV2ER_BASE_DIR/config/main_config.yml and
$CLEV2ER_BASE_DIR/config/chain_configs/testchain.yml

To find all the command line options for *run_chain.py*, type:

`python run_chain.py -h`

For further info, please see `clev2er.tools`

## Chain Configuration

A number of different YML format configuration files are passed to
the chain's algorithms, via a merged python dictionary.

### Main Configuration

The default chain configuration file is `$CLEV2ER_BASE_DIR/config/main_config.yml`

This contains general default settings for the chain controller. Each of these can
be overridden by the relevant command line options.

| Setting | Options | Description |
| ------- | ------- | ----------- |
| use_multi_processing | true or false | if true multi-processing is used |
| use_shared_memory | true or false | if true allow use of shared memory. Experimental feature |
| stop_on_error | true or false | stop chain on first error found, or log error and skip |

### Chain Specific Configuration

The default chain specific configuration file is
`$CLEV2ER_BASE_DIR/config/chain_configs/<chain_name>_<BVVV>.yml`

where B is the baseline character A..Z, and VVV is the zero padded version.

If no baseline and version are used, then you can use

`$CLEV2ER_BASE_DIR/config/chain_configs/<chain_name>.yml`

There are no specific rules for chain configuration file settings other than use of 
the YML format. The requirement for specific settings are set by the chain and it's algorithms.
An example of a chain configuration file can be found at:

`$CLEV2ER_BASE_DIR/config/chain_configs/cryotempo_C001.yml`


## Developing New Chains

1. Decide on a chain name. For example **newchain**
2. Create $CLEV2ER_BASE_DIR/algorithms/**newchain**/ directory to store the new chain's algorithms.
3. Create $CLEV2ER_BASE_DIR/algorithms/**newchain**/tests to store the new chain's 
   algorithm unit tests (using tests formatted for pytest). At least one algorithm test file 
   should be created per algorithm, which should contain suitable test functions.
4. Create your algorithms by copying and renaming the algorithm class template 
   $CLEV2ER_BASE_DIR/algorithms/testchain/testalg1.py in to your algorithm directory. Each algorithm
   should have a different file name of your choice. For example: alg_retrack.py, alg_geolocate.py. 
   You need to fill in the appropriate sections of the init(), process() and finalize() functions 
   for each algorithm (see section below for more details on using algorithm classes).
5. Each algorithm and their unit tests must pass the static code checks (pylint, mypy, etc) which 
   are automatically run as git pre-commit hooks. 
6. Create a YML configuration file for the chain in 
   $CLEV2ER_BASE_DIR/config/chain_configs/**newchain**.yml. The configuration file contains
   any settings or resource locations that are required by your algorithms, and may include 
   environment variables.
   Note that you can also create a configuration file per baseline and version of your chain by 
   appending `_<BVVV>`. So for baseline A, version 1, you would use:
   $CLEV2ER_BASE_DIR/config/chain_configs/**newchain**_A001.yml
7. If required create one or more finder class files. These allow fine control of L1b file 
   selection from the command line (see section below for more details).
8. Create an algorithm list YML file in 
   $CLEV2ER_BASE_DIR/config/algorithm_lists/**newchain**.yml. 
   If you want to have multiple baselines and versions of your chain you can create one or 
   more algorithm lists using the syntax: 
   $CLEV2ER_BASE_DIR/config/algorithm_lists/**newchain**_A001.yml (where A is the baseline 
   character A-Z, and 001 is the version number).
9. To test your chain on a single L1b file, you can use 
   `run_chain.py --name newchain -f /path/to/a/l1b_file`. There are many options for running chains 
   (see `run_chain.py -h`).

## Developer Notes

### Automatic Documentation

This user manual is hosted on GitHub pages (https://cpomsoft.github.io/clev2er)

Content is created from doctrings
(optionally containing Markdown: https://www.markdownguide.org/basic-syntax/#code )
in the code,
using the *pdoc* package : https://pdoc.dev

Diagrams are implemented using mermaid: https://mermaid.js.org

The site is locally built in `$CLEV2ER_BASE_DIR/docs`, using a pre-commit hook
(hook id: pdocs_build).
Hooks are configured in `$CLEV2ER_BASE_DIR/.pre-commit-config.yaml`

The hook calls the script `$CLEV2ER_BASE_DIR/pdocs_build.sh` to build the site
whenever a `git commit` is run.

When a `git push` is run, GitHub automatically extracts the site from the
docs directory and publishes it.

The front page of the site (ie this page) is located in the doctring within
`$CLEV2ER_BASE_DIR/src/clev2er/__init__.py`.

The docstring within `__init__.py` of each package directory should provide
markdown to describe the directories beneath it.

"""
