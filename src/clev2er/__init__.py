"""
# CLEV2ER Algorithm Framework

**Pre-design** of an Algorithm framework for 
-   CryoTEMPO Land Ice : view the algorithms: `clev2er.algorithms.cryotempo`
-   CLEV2ER Land Ice and Inland Waters
-   Any other L1b->L2 chain

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

## Features

* Command line tool : src/clev2er/tools/run_chain.py
* input L1b file selection (single file or multiple files)
* dynamic algorithm loading from YML list(s)
  * algorithms are classes of type Algorithm with .__init__(), .process(), .finalize()
  * Algorithm.init() is called before any L1b file processing.
  * Algorithm.process() is called on every L1b file,
  * Algorithm.finalize() is called after all files have been processed.
  * Each algorithm has access to: l1b Dataset, shared working dict, config dict
* logging (+ multi-processing logging support)
* multi-processing (1 core per l1b file), configurable maximum number of cores.
* algorithm timing (with MP support)
* chain timing

## Packaging/Workflow

* pre-commit git hooks for automated static code analysis. 
These tools run whenever you do a `git commit`. 
The commit will fail if any of the tests fail for the following tools:  
    - lint
    - flake8
    - black
    - pylint
    - isort 
    - mypy 

* poetry package dependency management
* pdoc automated documentation to GitHub pages

## Installation

Make sure you have *git* installed on your system.  

Clone the git repository: 

with https:  
`git clone https://github.com/cpomsoft/clev2er.git`  

or with ssh:  
`git clone git@github.com:cpomsoft/clev2er.git`  

or with the GitHub CLI:  
`gh repo clone cpomsoft/clev2er`  

## Shell Environment Setup

The following shell environment variables need to be set. In a bash shell this might be 
done by adding export lines to your $HOME/.bash_profile file.  

Set the *CLEV2ER_BASE_DIR* environment variable to the root of the clev2er package.  Then set
the PYTHONPATH to point to the packages src directory. Here is an example:  

```script
export CLEV2ER_BASE_DIR=/Users/alanmuir/software/clev2er
export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src
export PATH=${CLEV2ER_BASE_DIR}/src/clev2er/tools:${PATH}
# for multi-processing/shared mem support set ulimit
# to make sure you have enough file descriptors available
ulimit -n 8192
```

## Python Requirement

Requires python v3.10 to be installed before proceeding.
A recommended minimal method of installation is using miniconda as follows 
(other appropriate methods may also be used):

Select the **python 3.10** installer for your operating system from:

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

This project uses *poetry* to manage package dependencies and virtual envs.

First, you need to install *poetry* on your system using instructions from
https://python-poetry.org/docs/#installation. Normally this just requires running:

`curl -sSL https://install.python-poetry.org | python3 -`

You should also then ensure that poetry is in your path, such that the command

`poetry --version`

returns the poetry version number. You may need to modify your 
PATH variable in order to achieve this.

Run the following command to install python dependencies for this package
(for info, it uses settings in pyproject.toml to know what to install)

### Install packages using Poetry

```
cd $CLEV2ER_BASE_DIR
poetry install
poetry update
```

Finally, to load the virtual env, type:  

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

## Chain Configuration

A number of different YML format configuration files are passed to
the chain's algorithms, via a merged python dictionary.

### Main Configuration

The default chain configuration file is `$CLEV2ER_BASE_DIR/config/main_config.yml`

This contains settings for :
- default location of log files (INFO, DEBUG,ERROR)
- default multi-processing settings (mp enabled/disabled, max number of cores)

### Chain Specific Configuration

The default chain specific configuration file is
`$CLEV2ER_BASE_DIR/config/chain_configs/<chain_name>_<BVVV>.yml`

## Example of Running the Chain

This example runs the processing chain *cryotempo* on every L1b file in
/path/to/l1b_files. It uses all the default configuration files for that chain.

```script
cd $CLEV2ER_BASE_DIR/src/clev2er/tools
python run_chain.py --name cryotempo -d /path/to/l1b_files
```

To find all the command line options for *run_chain.py*, type:

`python run_chain.py -h`

For further info, please see `clev2er.tools`

## Developer Notes

### Automatic documentation

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
