"""
# CLEV2ER Algorithm Framework

**Pre-design** of an Algorithm framework for 
-   CryoTEMPO Land Ice : view the algorithms: `clev2er.algorithms.cryotempo`
-   CLEV2ER Land Ice and Inland Waters
-   Any other L1b->L2 chain

## Features

* Command line tool : src/tools/run_chain.py
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

* pre-commit git hooks for static code analysis
* poetry package dependency management
* pdoc automated documentation to GitHub pages

## Installation

Clone the git repository: 

with https:  
`git clone https://github.com/cpomsoft/clev2er.git`  

or with ssh:  
`git clone git@github.com:cpomsoft/clev2er.git`  

or with the GitHub CLI:  
`gh repo clone cpomsoft/clev2er`  

## Environment Setup

The following environment variables need to be set. In a bash shell this might be done
by adding export lines to your $HOME/.bash_profile file.  

Set the *CLEV2ER_BASE_DIR* environment variable to the root of the clev2er package.  Then set
the PYTHONPATH to point to the packages src directory. Here is an example:  

```script
export CLEV2ER_BASE_DIR=/Users/alanmuir/software/clev2er
export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src
```

## Virtual Environment and Package Requirements

This project uses *poetry* to manage package dependencies and virtual envs.  

First, you need to install *poetry* on your system from 
https://python-poetry.org/docs/#installation.  

Run the following command to install python dependencies for this package
(for info, it uses settings in pyproject.toml to know what to install)

`poetry install`  

Finally, to load the virtual env, type:  

`poetry shell`  

You should now be setup to run processing chains, etc.


## Example of Running the Chain

This example runs the processing chain *cryotempo* on every L1b file in 
/path/to/l1b_files. It uses all the default configuration files for that chain.

```script
cd $CLEV2ER_BASE_DIR/src/clev2er/tools
python run_chain.py --name cryotempo -d /path/to/l1b_files
```

To find all the command line options for *run_chain.py*, type:  

`python run_chain.py -h`
"""
