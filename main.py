import os

import logging
import numpy as np
import polars as pl
import typing as tp

import modules.epa_query as epa
import modules.logging as log


# GLOBALS
INPUT = "input"
OUTPUT = "output"
logging.getLogger(__name__)


def main():
    # Simple logger
    log.configure_logger(f"{OUTPUT}/target_query.log")

    # Start collecting query results
    query_all_cycles = []

    for filename in sorted(os.listdir(INPUT)):

        # If there are rogue files, skip over them
        if filename.split(".")[-1] != "csv":
            continue

        cycle_frame = handle_single_file(filename)

        # Need to recast the data type of "system size"
        cycle_frame = cycle_frame.with_columns(
            pl.col("system_p-num").cast(pl.Float64).alias("system_p-num"),
            pl.col("system_s-num").cast(pl.Float64).alias("system_s-num")
        )

        query_all_cycles.append(cycle_frame)

    # Save a combination of all queries
    query_all_cycles = pl.concat(query_all_cycles).sort(by="planet_name")
    save_parameters(query_all_cycles, "all")

    # Print final message to terminal
    print("QUERY COMPLETED. MAKE SURE TO CHECK LOG-FILE.\n")

    return


def handle_single_file(filename: str) -> pl.DataFrame:
    """Perform standardised query for one input file"""
    logging.info(f"Compiling results for {filename}")
    print(f"Compiling results for {filename}")

    cycle_frame, cycle_n = read_jwst_cycle(filename=filename)

    # Make unique list of planet names to query
    unique_names = cycle_frame.unique(
        subset=["planet_name"],
        maintain_order=True
    )
    query_names = unique_names["planet_name"].to_numpy()

    # Query EPA and update existing data frame
    query_result = pl.from_pandas(epa.query_nasa_epa(query_names))
    combined_frame = update_frame(cycle_frame, query_result)

    # Save full and reduced frame
    logging.info("Saving results...\n")
    save_parameters(combined_frame, cycle_n)

    return combined_frame


def read_jwst_cycle(filename: str) -> tuple[pl.DataFrame, int]:
    """Reading individual cycle files."""
    # ToDo: Not the best solution, very static
    cycle_number = int(filename.split(".")[0][-1])

    # Read file contents and add cycle indicator
    jwst_frame = pl.read_csv(f"{INPUT}/{filename}")
    jwst_frame = jwst_frame.with_columns(
        pl.lit(cycle_number).alias("jwst_cycle")
    )

    return jwst_frame, cycle_number


def update_frame(
        parent_frame: pl.DataFrame,
        child_frame: pl.DataFrame
        ) -> pl.DataFrame:
    """Update existing data frame with queried parameters."""
    # Add columns names unique to queried values
    queried_columns = np.setdiff1d(
        child_frame.columns, parent_frame.columns
    )

    # Construct a finalised frame extending the initial parameters
    final_frame = parent_frame.with_columns([
        pl.lit(np.nan).alias(column_name)
        for column_name in queried_columns
    ])

    # Update the rows of finalised frame through iteration
    temporary_dictionary = [
        update_rows(element, child_frame)
        for element in final_frame.iter_rows(named=True)
    ]

    # Sort the results by planet name
    finalised = pl.DataFrame(temporary_dictionary).sort(by="planet_name")

    return finalised


def update_rows(row_dict: dict, query_result: pl.DataFrame) -> dict:
    """
    Update individual row of data frame, represented as dictionary.
    Also incorporates failed queries
    """
    try:
        relevant_query = query_result.row(
            by_predicate=(pl.col("planet_name") == row_dict["planet_name"]),
            named=True
        )
        for key, value in relevant_query.items():
            row_dict[key] = value

    except pl.exceptions.NoRowsReturnedError:
        # This skips over failed queries (which are noted in the log-file)
        pass

    return row_dict


def save_parameters(
        total_frame: pl.DataFrame, cycle_number: tp.Union[int, str]
        ) -> None:
    "Save several versions of the full query frame."
    # First, save the full data frame
    total_frame.write_csv(
        file=f"{OUTPUT}/parameters_full/jtp_full_cycle-{cycle_number}.csv"
    )

    # Select necessary reduced parameters
    intial_parameters = [
        "planet_name", "jwst_instrument", "jwst_filter", "jwst_dispersion",
        "type", "num_obs", "jwst_cycle", "pid", "eap_months"
    ]
    planet_parameters = [
        "radius_rearth", "mass_mearth", "period_day", "sma_au",
        "eq-temp_kelvin",
    ]
    star_parameters = [
        "host_name", "system_p-num", "system_s-num",
        "system-distance_pc", "star-teff_kelvin",
        "star-radius_rsol", "star-mass_msol", "star-log10-lbol_lsol",
        "star-age_ga", "star-rotvel_kms"

    ]
    selection = intial_parameters + planet_parameters + star_parameters

    # Save a reduced frame
    total_frame[selection].write_csv(
        file=f"{OUTPUT}/jtp_cycle-{cycle_number}.csv"
    )

    return None


if __name__ == "__main__":
    main()
