# line-too-long, pylint: disable=C0301
# flake8: noqa
"""
## Tools Directory ##

This directory contains command-line tools required to run the chains.

### Tools List ###

- `clev2er.tools.run_chain`

### Example of Running the Chain

This example runs the processing chain *cryotempo* on every L1b file in 
/path/to/l1b_files. It uses all the default configuration files for that chain.

```script
cd $CLEV2ER_BASE_DIR/src/clev2er/tools
python run_chain.py --name cryotempo -d /path/to/l1b_files
```

To find all the command line options for *run_chain.py*, type:  

`run_chain.py --help`

| Argument      | Short Arg | Description |
| ----------- | ----------- |----------- |
| --name      | -n | name (str) : chain name    |
| --alglist   | -a | [Optional, str] path of algorithm list YML file. Default is ${CLEV2ER_BASE_DIR}/config/algorithm_lists/*chainname*.yml   |
| --conf      | -c | [Optional, str] path of main YAML configuration file. Default is $CLEV2ER_BASE_DIR/config/main_config.yml   |
| --baseline  | -b | [Optional, char] baseline of chain. Single uppercase char. Default=A. Used to specify the chain config file, where config file = $CLEV2ER_BASE_DIR/config/chain_configs/*chainname*_*BVVV*.yml  |
| --version   | -v | [Optional, char] version of chain. integer 1-100. Default=1. Used to specify the chain config file, where config file = $CLEV2ER_BASE_DIR/config/chain_configs/*chainname*_*BVVV*.yml  |
| --file      | -f | [Optional, str] path of input L1b file  |
| --dir       | -d | [Optional, str] path of dir containing input L1b files  |
| --max_files | -mf | [Optional, int] limit number of L1b files input to first n  |
| --quiet     | -q | [Optional] do not output log messages to stdout  |
| --debug     | -de | [Optional] log.DEBUG messages are output to log file, and stdout  |
| --multiprocessing | -mp | [Optional] use multi-processing, overrides main config file setting  |
| --sequentialprocessing | -sp | [Optional] use sequential processing, overrides main config file setting  |
| --nprocs | -np | [Optional,int] maximum number of cores to split multi-processing on. Overrides setting in main config |
| --sharedmem | -sm | [Optional] use shared memory when multi-processing is enabled. Experimental feature |
| --stop_on_error | -st | [Optional] stop chain on first error. Default is set in main config file |
| --logstring | -ls | [Optional, str] append this string to log file names for this run, as <logfilename>_<this_string>.log |
| --year | -y | [Optional, int] year number (YYYY) to use to select L1b files. The year number is used by the chain's finder |
| --month | -m | [Optional, int] month number (1,12) to use to select L1b files. The month number is used by the chain's finder algorithms if they support month selections |
| --find_opts | -fo | [Optional, str,str]  Comma separated list of string options to pass to l1b finder algorithms. |
| --cs2testdir | -ct | [Optional] for quick CS2 tests, uses default CS2 L1b directory: $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles |

"""
