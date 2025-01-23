from copy import deepcopy
import numpy as np
import pandas as pd
import matplotlib as mpl
from typing import Union


def rc_setup():
    """Generalized plot attributes"""
    mpl.rcParams["xtick.direction"] = "in"
    mpl.rcParams["xtick.labelsize"] = "large"
    mpl.rcParams["xtick.major.width"] = 1.5
    mpl.rcParams["xtick.minor.width"] = 1.5
    mpl.rcParams["xtick.minor.visible"] = "True"
    mpl.rcParams["xtick.top"] = "True"

    mpl.rcParams["ytick.direction"] = "in"
    mpl.rcParams["ytick.labelsize"] = "large"
    mpl.rcParams["ytick.major.width"] = 1.5
    mpl.rcParams["ytick.minor.width"] = 1.5
    mpl.rcParams["ytick.minor.visible"] = "True"
    mpl.rcParams["ytick.right"] = "True"

    mpl.rcParams["lines.markersize"] = 10

    mpl.rcParams["axes.linewidth"] = 1.5
    mpl.rcParams["axes.labelsize"] = "large"


def cycle1_selection(target_df: pd.DataFrame, obs_type: str) -> pd.DataFrame:
    """
    Changes the dictionary target list of JWST cycle 1 targets by
    throwing out:
        1. Only 'obs_type' observations
        2. Duplicate entries
        3. Targets with missing values (this is why GJ 4102 b is missing)
        4. Only including sub-Neptune sized planets (<= 4 R_e)
    """
    # Make a copy of input to return
    # target_list = deepcopy(target_list_raw)
    list_obsonly = target_df.loc[target_df["Type"] == obs_type]

    # Make the data frame unique and filter out NaN values from
    # important columns
    unique_obsonly = list_obsonly.drop_duplicates(
        subset=['Target Name', 'EAP [mon]']
    )

    print(f"{len(unique_obsonly)} targets before value drop!\n ")

    checknan_obsonly = unique_obsonly.dropna(
        subset=['Radius [RE]', 'Teff [K]', 'SMA [au]']
    )

    # Sort for super-Earths and mini-Neptunes
    #ind_upperrad = np.where(target_list["Radius [RE]"] <= 3.)[0]
    #red_total_dict(target_list, ind_upperrad)

    #ind_lowerrad = np.where(target_list["Radius [RE]"] > 0.)[0]
    #red_total_dict(target_list, ind_lowerrad)

    return checknan_obsonly


def fill_arr(str_array: np.array, filler: Union[str, float, int]):
    """
    Helper function: fills empty entries in array with predefined filler
    value.
    """
    for i in range(len(str_array)):
        if str_array[i] == "":
            str_array[i] = filler

    return str_array


def red_total_dict(target_dict: dict, index_list: np.array) -> dict:
    """
    Reduces all keyed entries of a dictionary by a given index list.
    """
    dict_keys = list(target_dict.keys())

    # Reduce all dictionary entries
    for key in dict_keys:
        target_dict[key] = target_dict[key][index_list]

    return target_dict


def make_dict_unique(target_dict: dict) -> dict:
    """
    Reduces a given dictionary by duplicate entries, looping through all
    dictionary keys.
     """
    dict_keys = list(target_dict.keys())

    # Find unique indices by target name (first key)
    _, u_indices = np.unique(target_dict[dict_keys[0]], return_index=True)

    # Reduce all dictionary entries
    for key in dict_keys:
        target_dict[key] = target_dict[key][u_indices]

    return target_dict


def check_nans(target_dict: dict) -> dict:
    """Reduces a given dictionary by NaN-entries."""
    dict_keys = list(target_dict.keys())

    # TODO: Numpy throws a FutureWarning here
    by_column = [list(np.where(target_dict[key] != 0.)[0])
                 for key in dict_keys]
    nan_ind = np.unique(np.array(sum(by_column, [])))

    # Reduce all dictionary entries
    for key in dict_keys:
        target_dict[key] = target_dict[key][nan_ind]

    return target_dict


def combine_transit_eclipse(transit_dict, eclipse_dict):
    """Specifically to combine transit and eclipse observations"""
    transit_len = len(transit_dict["Target Name"])
    eclipse_len = len(eclipse_dict["Target Name"])

    transit_dict["Transit"] = np.ones(transit_len)
    transit_dict["Eclipse"] = np.zeros(transit_len)

    eclipse_dict["Transit"] = np.zeros(eclipse_len)
    eclipse_dict["Eclipse"] = np.ones(eclipse_len)

    # DOCSTRING
    eclipse_remove = []

    for name in eclipse_dict["Target Name"]:
        if name in transit_dict["Target Name"]:

            transit_idx = np.where(transit_dict["Target Name"] == name)[0]
            transit_dict["Eclipse"][transit_idx] = 1

            eclipse_remove.append(
                np.where(eclipse_dict["Target Name"] == name)[0][0]
            )

    # Remove duplicate entries from eclipse dictionary
    for key, value in eclipse_dict.items():
        eclipse_dict[key] = np.delete(eclipse_dict[key], eclipse_remove)

    # Use pandas data frames from now on
    transit_frame = pd.DataFrame.from_dict(transit_dict)
    eclipse_frame = pd.DataFrame.from_dict(eclipse_dict)

    # Generate final full frame
    full_frame = pd.concat([transit_frame, eclipse_frame],
                           ignore_index=True)

    return full_frame


def plotable_hz_bounds(temp=np.linspace(2600, 7200, 5000),
                       lbol=np.linspace(0.01, 1, 5000)) -> dict:
    """Returns a dictionary of inner and outer HZ boundary distances."""
    bounds = ["oi", "ci", "co", "oo"]
    hz_bounds = {
        key: habitable_zone_distance(temp, lbol, key)
        for key in bounds
    }

    return hz_bounds


def habitable_zone_distance(effect_temp, lum, est_ident):
    """
    HZ estimation from Kopparapu et al. (2013, 2014).

    :param effect_temp: NDARRAY, Stellar temperature in Kelvin
    :param lum: NDARRAY, Stellar bolometric luminosity in solar units
    :param est_ident: STR, Identifier for the estimation boundary

    :return: NDARRAY, HZ distance in AU
    """

    # Determine valid indicators
    valid_ind = ["oi", "ci", "co", "oo"]
    est_indices = dict(zip(valid_ind, range(4)))

    # SANITY CHECK: indicator for estimate must exist
    assert est_ident.lower() in ["oi", "ci", "co", "oo"], \
        f"INDICATOR {est_ident} FOR ESTIMATION METHOD NOT RECOGNIZED!"

    # Parameter matrix organized by oi, ci, co, oo estimates
    # PLEASE NOTE THE ERRATUM TO THE ORIGINAL KOPPARAPU (2013) PAPER!
    param = np.array([
        [1.4335e-4, 3.3954e-9, -7.6364e-12, -1.1950e-15],
        [1.2456e-4, 1.4612e-8, -7.6345e-12, -1.7511e-15],
        [5.9578e-5, 1.6707e-9, -3.0058e-12, -5.1925e-16],
        [5.4471e-5, 1.5275e-9, -2.1709e-12, -3.8282e-16],
    ])

    # Set correct param-subindex according to est_ident
    est_index = est_indices[est_ident]

    # Call the S_eff calculation function with correct parameters
    s_eff = effective_flux(param[est_index], effect_temp, est_index)

    # Calculate distance
    distance = np.sqrt(lum / s_eff)

    return distance


def effective_flux(param_list, effect_temp, estimation_index):
    """Intermediate step in HZ calculation"""
    s_effsun = [1.7763, 1.0385, 0.3507, 0.3207]

    # Temperature array consisting of powers 1 to 4
    temp = np.array(
        [(effect_temp - 5780) ** (i + 1) for i in range(4)]
    )

    # Transpose the temperature-power array to have each row be a list
    # of Temp ** 1 to Temp ** 4, and then calculate the dot-product
    # with the parameter list vector
    return s_effsun[estimation_index] + temp.T @ param_list
