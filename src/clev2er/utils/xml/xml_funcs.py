"""xml processing functions"""

import os
import re


def replace_env_variables(input_str):
    """replace environment variables in str

    copes with $SOME_ENV and ${SOME_ENV} in str

    Args:
        input_str (str): input string

    Returns:
        str: string with env vars replaced
    """
    # Regular expression to find environment variable placeholders
    env_var_pattern = r"\$(\w+)|\${(\w+)}"

    def replace_match(match):
        # Extract the environment variable name from the match
        var_name = match.group(1) or match.group(2)
        # Get the value of the environment variable or return an empty string if not found
        var_value = os.environ.get(var_name, "")
        return var_value

    # Use re.sub to replace all matches with their corresponding values
    result_str = re.sub(env_var_pattern, replace_match, input_str)
    return result_str


def set_xml_dict_types(config: dict) -> None:
    """convert string values to bool, int, float in a dict parsed from xml

    xmltodict.parse(xml) creates a dictionary from the XML file
    but it stores all dict values as type str

    This function checks each string and converts to :
        bool : if str == 'false' (any case) == 'true (any case)
        int : if int(str) is valid
        float : if float(str) is valid

    Args:
        config (dict): dictionary previously parsed by xmltodict

    Returns:
        None

    """
    for key, value in config.items():
        if isinstance(value, dict):
            set_xml_dict_types(value)
        else:
            if value.lower() == "false":
                config[key] = False
            elif value.lower() == "true":
                config[key] = True
            elif "$" in value:
                envs_expanded_str = replace_env_variables(value)
                config[key] = envs_expanded_str
            else:
                try:
                    config[key] = int(config[key])
                except ValueError:
                    try:
                        config[key] = float(config[key])
                    except ValueError:
                        pass
