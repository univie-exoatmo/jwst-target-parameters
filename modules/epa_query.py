import pyvo
import pandas as pd
import logging as log
import numpy as np

# GLOBALS
QUERY_PARAMETERS = {
    # Auxiliary information
    "pl_name": "planet_name", "sy_pnum": "system_p-num",
    "sy_snum": "system_s-num",
    "hostname": "host_name", "pl_letter": "planet_id",
    "sy_dist": ("system-distance", "pc"),
    # Planet parameters
    "pl_orbper": ("period", "day"), "pl_orbsmax": ("sma", "au"),
    "pl_rade": ("radius", "rearth"), "pl_bmasse": ("mass", "mearth"),
    "pl_eqt": ("eq-temp", "kelvin"),
    # Stellar parameters
    "st_teff": ("star-teff", "kelvin"), "st_rad": ("star-radius", "rsol"),
    "st_mass": ("star-mass", "msol"), "st_lum": ("star-log10-lbol", "lsol"),
    "st_age": ("star-age", "ga"), "st_vsin": ("star-rotvel", "kms"),
}


def assign_query_parameters(
        epa_name: str, table_name: str, unit: str
        ) -> dict:
    """Utility to homogeneously assign query parameter names."""
    # Conveniently enough, the EPA has unified their parameter naming scheme
    parameter_set = {
        epa_name: f"{table_name}_{unit}",
        f"{epa_name}err1": f"{table_name}_errpos",
        f"{epa_name}err2": f"{table_name}_errneg",
        f"{epa_name}_reflink": f"{table_name}_ref",
        # Removing the "limit" keyword for now, will need some time to
        # incorporate this
        # f"{epa_name}lim": f"{table_name}_limit",
    }

    return parameter_set


def construct_adql_query(
        planet_names: np.ndarray,
        query_parameter_list: dict
        ) -> str:
    """Construct a string to query the exoplanet archive through TAP"""
    # Construct correct query-related strings
    selection_string = string_from_list(list(query_parameter_list.keys()))
    name_sequence = string_from_list(list(planet_names), "'")

    # Base query: Search in the "planetary system composite"
    # (or pscomppars) table (rather than the ps table)
    base_str = f"SELECT {selection_string} FROM pscomppars "
    query_name = f"WHERE pl_name IN ({name_sequence})"

    # Log information about the queried table
    log.info(
        "All queries are made to the 'pscomppars' table "
        "(https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html) "
        ", which means they might not be entirely self-consistent!")

    return f"{base_str}{query_name}"


def create_query_parameter_catalogue(parameter_list: dict) -> dict:
    """Create extended parameter catalogue to query the EPA."""
    # Define exceptions from the standardised name space
    exceptions = ["pl_name", "sy_pnum", "sy_snum", "hostname", "pl_letter"]

    # Return dictionary (this routine will make use of "|" to merge dicts)
    finalised_dictionary = {}

    # Loop over all parameter values
    for key, value in parameter_list.items():

        # If in exceptions, only return the initial pair
        if key in exceptions:
            finalised_dictionary = finalised_dictionary | {key: value}

        else:
            my_name, phys_unit = value
            temporary_dict = assign_query_parameters(key, my_name, phys_unit)
            finalised_dictionary = finalised_dictionary | temporary_dict

    return finalised_dictionary


def query_nasa_epa(target_names: np.ndarray) -> pd.DataFrame:
    """
    Query the NASA Exoplanet Archive using TAP through pyVO. The
    values returned here are the ones flagged as "default" in the EPA
    catalogue.
    """
    # Set up NASA EPA query with pyVO
    tap_source = "https://exoplanetarchive.ipac.caltech.edu/TAP"
    service = pyvo.dal.TAPService(tap_source)

    # Generate comprehensive query parameters
    full_query_list = create_query_parameter_catalogue(QUERY_PARAMETERS)

    # Construct ADQL query
    log.info(f"Querying NASA EPA for {target_names.shape[0]} targets:\n"
             f"{target_names}")
    adql_query = construct_adql_query(target_names, full_query_list)

    # Use pyVO to query NASA EPA
    result_table = service.search(adql_query)  # type: ignore

    # Sanity check: No targets are lost in the query
    # (ONLY A WARNING FOR NOW)
    lost_targets = np.setxor1d(target_names, result_table["pl_name"])

    if lost_targets.size == 0:
        log.info("All targets queried successfully!")
    else:
        log.warning(
            f"The following {lost_targets.shape[0]} target(s) could "
            f"not be queried in the EPA:\n{lost_targets}"
        )

    # Make into pandas frame
    pandas_frame = result_table.to_table().to_pandas()
    pandas_frame.rename(columns=full_query_list, inplace=True)

    return pandas_frame


def string_from_list(names: list, qualifier: str = "") -> str:
    """
    Construct a string of comma-separated values from a list.
    An optional qualifier can be wrapped around list-entries.
    """
    name_sequence = ""
    for name in names:
        name_sequence += f"{qualifier}{name}{qualifier},"

    # THIS removes the trailing comma
    name_sequence = name_sequence[:-1]

    return name_sequence
