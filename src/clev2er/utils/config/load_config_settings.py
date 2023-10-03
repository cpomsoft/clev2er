"""utils.config.load_config_settings.py

Common functions to load chain configuration files

load_algorithm_list(chain_name: str, baseline: str = "", version=0) -> list[str],list[str]
load_config_files(chain_name: str, baseline: str = "") -> dict:

"""

import glob
import logging
import os
import string
from typing import Tuple

import xmltodict  # for parsing xml to python dict
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)

from clev2er.utils.xml.xml_funcs import set_xml_dict_types

# pylint: disable=too-many-statements
# pylint: disable=too-many-locals


module_log = logging.getLogger(__name__)


# pylint: disable=too-many-branches


def load_algorithm_list(
    chain_name: str,
    baseline: str = "",
    version: int = 0,
    alg_list_file="",
    log: logging.Logger | None = None,
) -> Tuple[list, list, str]:
    """load algorithm and L1b finder list for specified chain

    Lists of algorithms and finder modules are either stored in XML or YML formats

    $CLEV2ER_BASE_DIR/config/algorithm_lists/chain_name_BVVV.[xml,.yml]

    Search rules:

    if baseline or version not specified search for the baseline or version
    with the highest baseline char (Z highest) and then highest version number of that baseline.

    if both xml and yml files exist for the same baseline/version then the xml file
    will have priority.

    Args:
        chain_name (str): name of the chain to load
        baseline (str, optional): specify baseline char to use [A-Z], default is "" which means
                                  unspecified and will search for the list with the highest
                                  (close to Z) baseline.
        version (int, optional): version number 1.., default=0 (unspecified, search for highest
                                  version found for baseline)

        alg_list_file (str,optional): path of algorithm list file to use. default="" which means
                                      search for one in standard locations
        log (logging.Logger, optional): log instance to use, default is None (use module loggger)
    Raises: KeyError,ValueError,OSError,NameError

    Returns:
        list[str], list[str], str: list of algorithm names,
                              list of finder module names - may be empty list, filename of algorithm
                              list used
    """

    if log is None:
        log = module_log

    if not alg_list_file:
        base_dir = os.environ["CLEV2ER_BASE_DIR"]

        algorithm_list_dir = f"{base_dir}/config/algorithm_lists"

        if not os.path.isdir(algorithm_list_dir):
            raise OSError(
                f"Could not find algorithm list directory : {algorithm_list_dir}"
            )

        if version < 0 or version > 100:
            raise ValueError(f"version ({version}) must be between 1 and 100")

        if baseline:
            if not baseline.isalpha():
                raise ValueError(f"baseline ({baseline}) must be a char between A..Z")
            baseline = baseline.upper()

        # ---------------------------------------------
        # Find algorithm list filename for this chain
        # ---------------------------------------------
        if version > 0 and baseline:
            # In this case we know exactly which name to use
            alg_list_file = (
                f"{base_dir}/config/algorithm_lists/"
                f"{chain_name}_{baseline}{version:03d}.xml"
            )
            if not os.path.isfile(alg_list_file):
                alg_list_file = (
                    f"{base_dir}/config/algorithm_lists/"
                    f"{chain_name}_{baseline}{version:03d}.yml"
                )

        else:  # We need to search for the highest baseline and then version
            # Load algorithm list by finding latest chain baseline
            # ie baseline B before A
            alg_list_file = []
            if baseline:
                reverse_alphabet_list = [baseline]
            else:
                reverse_alphabet_list = list(string.ascii_uppercase[::-1])
            for _baseline in reverse_alphabet_list:
                _alg_list_file = glob.glob(
                    f"{base_dir}/config/algorithm_lists/{chain_name}_{_baseline}*.xml"
                )
                if len(_alg_list_file) > 0:
                    baseline = _baseline
                    alg_list_file = _alg_list_file
                    break

                _alg_list_file = glob.glob(
                    f"{base_dir}/config/algorithm_lists/{chain_name}_{_baseline}*.yml"
                )
                if len(_alg_list_file) > 0:
                    baseline = _baseline
                    alg_list_file = _alg_list_file
                    break

            if len(alg_list_file) < 1:
                raise OSError(f"No algorithm list file found for chain {chain_name}")

            # find highest of multiple versions
            alg_list_file = alg_list_file[-1]

    log.info("Algorithm list file used: %s", alg_list_file)

    # --------------------------------------------------------------------------------
    # Read lists from file
    #
    # xml format:
    #
    # <algorithm_list>
    # <algorithms>
    #     <alg_template1>Enable</alg_template1>
    #     <alg_template2>Enable</alg_template2>
    # </algorithms>
    # <l1b_file_selectors>
    #     <module1_name>Enable</module1_name>
    # </l1b_file_selectors>
    # </algorithm_list>
    #
    # --------------------------------------------------------------------------------

    algorithm_list = []
    finder_module_list = []

    if alg_list_file[-4:] == ".xml":
        # Load XML file
        with open(alg_list_file, "r", encoding="utf-8") as file:
            list_xml = file.read()

        # Use xmltodict to parse and convert the XML document
        try:
            xml_dict = dict(xmltodict.parse(list_xml))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise OSError(f"{alg_list_file} xml format error : {exc}") from exc

        # Remove the root xml level as we don't need it
        algorithms_dict = xml_dict["algorithm_list"]["algorithms"]
        if "l1b_file_selectors" in xml_dict["algorithm_list"]:
            file_finders_dict = xml_dict["algorithm_list"]["l1b_file_selectors"]
        else:
            file_finders_dict = {}

        if file_finders_dict is not None:
            finder_module_list = list(file_finders_dict.keys())
            for finder_module in finder_module_list:
                if file_finders_dict[finder_module] == "Disable":
                    finder_module_list.remove(finder_module)
        algorithm_list = list(algorithms_dict.keys())
        for alg_module in algorithm_list:
            if algorithms_dict[alg_module] == "Disable":
                algorithm_list.remove(alg_module)

    elif alg_list_file[-4:] == ".yml":
        # Load YML file
        try:
            yml = EnvYAML(alg_list_file)  # read the YML and parse environment variables
        except ValueError as exc:
            raise ValueError(
                f"ERROR: algorithm list file {alg_list_file} has invalid"
                f"or unset environment variables : {exc}",
            ) from exc

        # Extract the algorithms list from the dictionary read from the YAML file
        try:
            algorithm_list = yml["algorithms"]
        except KeyError as exc:
            raise KeyError(
                f"ERROR: algorithm list file {alg_list_file} has missing key: {exc}",
            ) from exc

        # Extract the algorithms list from the dictionary read from the YAML file
        try:
            finder_module_list = yml["l1b_file_selectors"]
        except KeyError as exc:
            raise KeyError(
                f"ERROR: algorithm list file {alg_list_file} has missing key: {exc}",
            ) from exc

    else:
        raise NameError(
            f"Wrong file extension: {alg_list_file[-4:]} must be .yml or .xml in file "
            f": {alg_list_file}"
        )

    return algorithm_list, finder_module_list, alg_list_file


def load_config_files(
    chain_name: str,
    baseline: str = "",
    version: int = 0,
    main_config_file: str = "",
    chain_config_file: str = "",
) -> tuple[dict, str, int, str, str]:
    """function to load XML,or YML configuration files for a chain and return
       as a python dict

    Configuration files consist of:

    $CLEV2ER_BASE_DIR/config/main_config.xml

    +

    $CLEV2ER_BASE_DIR/config/chain_configs/{chain_name}_BVVV.yml
    where B is a char A..Z representing the baseline
    VVV is a zero padded int (1..100).
    If not specified the highest BVVV is chosen where a config file exists

    Args:
        chain_name (str) : name of the chain to load
        baseline (str, optional): baseline char A..Z, default="" (none specified)
                                  in which case the highest baseline (close to Z) is found
        version (int): version of config file, 1-100, def=0 (search for highest available version)
        main_config_file (str) : path of main chain config file, def=empty str (default path)
        chain_config_file (str) : path of chain config file, def=empty str
                                 (search highest available baseline, version)
    Raises: KeyError, OSError, ValueError

    Returns:
        (dict,str,int,str,str) : config dict, baseline, version
    """
    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    log = module_log

    # --------------------------------------------
    # Load main run control XML config file
    #   $CLEV2ER_BASE_DIR/config/main_config.xml
    # --------------------------------------------

    if not main_config_file:
        config_file = f"{base_dir}/config/main_config.xml"
    else:
        config_file = main_config_file
    if not os.path.exists(config_file):
        raise OSError(f"{config_file} not found")

    with open(config_file, "r", encoding="utf-8") as file:
        config_xml = file.read()

    # Use xmltodict to parse and convert the XML document
    try:
        config = dict(xmltodict.parse(config_xml))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise OSError(f"{config_file} xml format error : {exc}") from exc

    # Convert all str values from XML to correct types: bool, int, float, str
    # and evaluate env variables
    set_xml_dict_types(config)

    _main_config_file = config_file

    log.info("Using Main config file %s", config_file)

    # --------------------------------------------
    # Load chain config file by finding latest chain baseline
    # ie baseline B before A, and then highest version: VVV
    # --------------------------------------------

    if not chain_config_file:
        if baseline and version:
            chain_config_file = (
                f"{base_dir}/config/chain_configs/"
                f"{chain_name}_{baseline}{version:03d}.yml"
            )
            if not os.path.isfile(chain_config_file):
                chain_config_file = (
                    f"{base_dir}/config/chain_configs/"
                    f"{chain_name}_{baseline}{version:03d}.xml"
                )

        else:  # find one
            chain_config_file = ""
            if baseline:
                reverse_alphabet_list = [baseline]
            else:
                reverse_alphabet_list = list(string.ascii_uppercase[::-1])
            for _baseline in reverse_alphabet_list:
                if version:
                    _config_file = glob.glob(
                        f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}{version:03d}.xml"
                    )
                else:
                    _config_file = glob.glob(
                        f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}*.xml"
                    )
                if len(_config_file) > 0:
                    baseline = _baseline
                    chain_config_file = _config_file[-1]
                    break
                if version:
                    _config_file = glob.glob(
                        f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}{version:03d}.yml"
                    )
                else:
                    _config_file = glob.glob(
                        f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}*.yml"
                    )
                if len(_config_file) > 0:
                    baseline = _baseline
                    chain_config_file = _config_file[-1]
                    break
    else:
        baseline = chain_config_file[-8]
        if not baseline.isalpha():
            raise NameError(
                "chain config file must include a valid baseline char (end in BVVV.xml,yml)"
            )
        version = int(chain_config_file[-7:-4])
        if version < 0 or version > 100:
            raise ValueError(
                "chain config file must include a valid zero padded int version string VVV "
                "(name ends end in BVVV.xml,yml, ie ...C001.xml)"
            )
    if not chain_config_file:
        raise OSError(f"No chain config file found for chain {chain_name}")

    log.info("chain config: %s", chain_config_file)

    if chain_config_file[-4:] == ".xml":
        log.info("Using XML chain config file %s", chain_config_file)

        with open(chain_config_file, "r", encoding="utf-8") as file:
            config_xml = file.read()

        # Use xmltodict to parse and convert the XML document
        try:
            chain_config = dict(xmltodict.parse(config_xml))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise OSError(f"{config_file} xml format error : {exc}") from exc

        # Convert all str values from XML to correct types: bool, int, float, str
        # and evaluate env variables
        set_xml_dict_types(chain_config)

        # Remove the root xml level as we don't need it
        chain_config = chain_config["configuration"]

    if chain_config_file[-4:] == ".yml":
        log.info("Using YML chain config file %s", chain_config_file)

        chain_config = EnvYAML(
            chain_config_file
        ).export()  # read the YML and parse environment variables

    # override "chain" settings from chain_config if present
    if "chain" in chain_config:
        for key in chain_config["chain"]:
            if key in config["chain"]:
                config["chain"][key] = chain_config["chain"][key]
        chain_config.pop("chain", None)

    config = config | chain_config

    return config, baseline, version, _main_config_file, chain_config_file
