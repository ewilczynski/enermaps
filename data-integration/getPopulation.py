#!/usr/bin/env python3
"""
Get GISCO population dataset.
The original Excel file is downloaded and described using frictionless.
This script allows for data updates.

@author: giuseppeperonato
"""
import json
import logging
import os
import sys
import urllib

import frictionless
import pandas as pd
import utilities
from pandas_datapackage_reader import read_datapackage
from utilities import download_url

# Constants
OTHER_VARS = ["CNTR_CODE", "LAU_LABEL", "CNTR_LAU_CODE"]
SPATIAL_VARS = []  # manually set in prepare()
TIME_FORMAT = "POP_%Y_%m_%d"
VARIABLE = "Inhabitants"
UNITS = "[-]"
ISRASTER = False


logging.basicConfig(level=logging.INFO)

DB_URL = utilities.DB_URL


def prepare(dp: frictionless.package.Package, name: str):
    """

    Prepare data in EnerMaps format.

    Parameters
    ----------
    dp : frictionless.package.Package
        Valid datapackage
    name : str
        Name of the dataset (used for constructing the FID)

    Returns
    -------
    DataFrame
        Data in EnerMaps format.

    """
    logging.info("Reading Excel file from datapackage")
    data = read_datapackage(dp)

    value_vars = [x for x in data.columns if x not in OTHER_VARS + SPATIAL_VARS]

    value_vars_dt = pd.to_datetime(value_vars, format=TIME_FORMAT)

    data = data.rename(dict(zip(value_vars, value_vars_dt)), axis=1)

    # Unpivoting
    data = data.melt(id_vars=OTHER_VARS + SPATIAL_VARS, value_vars=value_vars_dt)

    # Remove nan
    data = data.dropna()

    # Add underscore to LAU code
    data["LAU_CODE"] = data["CNTR_CODE"] + "_" + data["CNTR_LAU_CODE"].str[2:]

    # Conversion
    enermaps_data = utilities.ENERMAPS_DF
    enermaps_data["fid"] = data["LAU_CODE"]
    enermaps_data["start_at"] = data["variable"]
    enermaps_data["value"] = data["value"]
    enermaps_data["variable"] = VARIABLE
    enermaps_data["unit"] = UNITS
    enermaps_data["israster"] = ISRASTER

    return enermaps_data


def get(url, dp, name="", force=False):
    """
    Retrieve data.

    Parameters
    ----------
    url : str
        URL to retrieve the data from.
    dp : frictionless.package
        Datapackage agains which validating the data.
    name : str, optional
        Name of the dataset.
    force : Boolean, optional
        If True, new data will be uploaded even if the same as in the db. The default is False.

    Returns
    -------
    DataFrame
        Data in EnerMaps format.
    frictionless.package
        Pakage descring the data.

    """
    if not os.path.exists("{}.xlsx".format(name)):
        logging.info("Downloading file...")
        download_url(url, "{}.xlsx".format(name))

    # Inferring and completing metadata
    logging.info("Creating datapackage for input data")
    new_dp = frictionless.describe_package("{}.xlsx".format(name), stats=True)
    new_dp.resources[0]["schema"].missing_values.append("-9999")
    # Correct columns wrongly inferred of "number" type due to missing value
    for field_idx in range(len(new_dp.resources[0]["schema"]["fields"])):
        if new_dp.resources[0]["schema"]["fields"][field_idx]["type"] == "integer":
            new_dp.resources[0]["schema"]["fields"][field_idx]["type"] = "number"

    # Logic for update
    if dp is not None:  # Existing dataset
        # check stats
        isChangedStats = dp["resources"][0]["stats"] != new_dp["resources"][0]["stats"]
        if "datePublished" in dp.keys():
            isChangedDate = dp["datePublished"] != new_dp["datePublished"]
        else:
            isChangedDate = False
        if (
            isChangedStats or isChangedDate
        ):  # Data integration will continue, regardless of force argument
            logging.info("Data has changed")
            if utilities.isDPvalid(dp, new_dp):
                enermaps_data = prepare(new_dp, name)
            else:
                return None, None
        elif force:  # Data integration will continue, even if data has not changed
            logging.info("Forced update")
            if utilities.isDPvalid(dp, new_dp):
                enermaps_data = prepare(new_dp, name)
            else:
                return None, None
        else:  # Data integration will stop here, returning Nones
            logging.info("Data has not changed. Use --force if you want to reupload.")
            return None, None
    else:  # New dataset
        dp = new_dp  # this is just for the sake of the schema control
        if utilities.isDPvalid(dp, new_dp):
            enermaps_data = prepare(new_dp, name)
        else:
            return None, None

    # Removing downloaded_file
    if os.path.exists("{}.xlsx".format(name)):
        os.remove("{}.xlsx".format(name))

    return enermaps_data, new_dp


if __name__ == "__main__":
    datasets = pd.read_csv("datasets.csv", index_col=[0])
    script_name = os.path.basename(sys.argv[0])
    ds_ids, isForced = utilities.parser(script_name, datasets)
    url = datasets.loc[
        datasets["di_script"] == os.path.basename(sys.argv[0]), "di_URL"
    ].values[0]
    name = urllib.parse.quote_plus(
        datasets.loc[
            datasets["di_script"] == script_name, "Title (with Hyperlink)"
        ].values[0]
    )
    for ds_id in ds_ids:
        dp = utilities.getDataPackage(ds_id, DB_URL)

        data, dp = get(url=url, dp=dp, name=name, force=isForced)

        if isinstance(data, pd.DataFrame):
            # Remove existing dataset
            if utilities.datasetExists(ds_id, DB_URL,):
                utilities.removeDataset(ds_id, DB_URL)
                logging.info("Removed existing dataset")

            # Create dataset table
            metadata = datasets.loc[ds_id].fillna("").to_dict()
            metadata["datapackage"] = dp
            metadata = json.dumps(metadata)
            dataset = pd.DataFrame([{"ds_id": ds_id, "metadata": metadata}])
            utilities.toPostgreSQL(
                dataset, DB_URL, schema="datasets",
            )

            # Create data table
            data["ds_id"] = ds_id
            utilities.toPostgreSQL(data, DB_URL, schema="data", chunksize=10000)
