# CLEV2ER Algorithm Framework

Pre-design of an Algorithm framework for CLEV2ER LI+IW project

## Features

* Command line tool : src/tools/run_chain.py
* input L1b file selection
* dynamic algorithm loading from YML list(s) : config/li_algorithm_list.yml, iw_algorithm_list.yml
* logging
* multi-processing (+logging support)
* algorithm timing
* chain timing

## Packaging/Workflow

* pre-commit git hooks
* poetry package dependency management
