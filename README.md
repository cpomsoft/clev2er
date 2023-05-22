# CLEV2ER Algorithm Framework

Pre-design of an Algorithm framework for CLEV2ER LI+IW project

## Features

* Command line tool : src/tools/run_chain.py
* input L1b file selection (single file or multiple files)
* dynamic algorithm loading from YML list(s) : config/li_algorithm_list.yml, iw_algorithm_list.yml
  * algorithms are classes of type Algorithm with .__init__(), .process(), .finalize()
  * .process() is called on every L1b file, init() before processing, finalize() after processing.
  * algorithms have access to: l1b Dataset, shared working dict, config dict
* logging (+ multi-processing logging support)
* multi-processing (1 core per l1b file), configurable number of cores.
* algorithm timing (with MP support)
* chain timing

## Packaging/Workflow

* pre-commit git hooks
* poetry package dependency management
