"""
# CLEV2ER Algorithm Framework

**Pre-design** of an Algorithm framework for 
-   CryoTEMPO Land Ice : `clev2er.algorithms.cryotempo`
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


"""
