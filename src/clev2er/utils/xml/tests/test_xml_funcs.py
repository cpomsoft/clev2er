""" test of xml_funcs.py functions"""
import os

import xmltodict

from clev2er.utils.xml.xml_funcs import set_xml_dict_types


def test_set_xml_dict_types():
    """test of set_xml_dict_types"""
    xml_config_file = f"{os.environ['CLEV2ER_BASE_DIR']}/config/main_config.xml"
    with open(xml_config_file, "r", encoding="utf-8") as file:
        my_xml = file.read()

    # Use xmltodict to parse and convert
    # the XML document
    try:
        config = dict(xmltodict.parse(my_xml))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        assert 0, f"error in xml : {exc}"
        return

    # Convert all str values to correct types: bool, int, float, str
    set_xml_dict_types(config)

    assert isinstance(config["chain"], dict)
    assert isinstance(config["chain"]["use_multi_processing"], bool)
    assert isinstance(config["chain"]["max_processes_for_multiprocessing"], int)
