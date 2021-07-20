#!/usr/bin/python
import io

import requests
from werkzeug.datastructures import FileStorage

from app.data_integration.data_config import DATASETS_DIC

DATASETS_SERVER_URL = "https://lab.idiap.ch/enermaps/api/"
DATASETS_SERVER_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYXBpX3VzZXIifQ.gzl3uCe1OdCjf3feliREDJFfNkMTiDkVFcVDrCNlpBU"

RASTER_SERVER_URL = "https://lab.idiap.ch/enermaps/raster/"


def get_datasets_metadata():
    url = DATASETS_SERVER_URL + "parameters"
    try:
        with requests.get(
            url, headers={"Authorization": "Bearer {}".format(DATASETS_SERVER_API_KEY)}
        ) as resp:
            resp_data = resp.json()
            return resp_data
    except ConnectionError:
        raise


def get_datasets_ids():
    """
    List the ids of the different datasets to be displayed
    """
    return [
        1,
        2,
        3,
        4,
        5,
        6,
        9,
        11,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        24,
        27,
        28,
        29,
        30,
        31,
        33,
        35,
        42,
        43,
        45,
        46,
        47,
        48,
        49,
        50,
    ]


def get_dataset(dataset_id, dataset_name):
    """
    Fetch a geojson dataset from the enermaps server with a given Id.
    """
    url = DATASETS_SERVER_URL + "rpc/enermaps_query_geojson"

    # Get the dataset parameters
    params = None
    layer_type = None
    for _, value in DATASETS_DIC.items():
        try:
            if value["id"] == dataset_id:
                params = value["json_params"]
                layer_type = value["layer_type"]
        except KeyError:
            raise

    if (params is not None) and (layer_type == "vector"):
        print("Fetching json dataset " + str(dataset_id))
        try:
            with requests.post(
                url,
                headers={"Authorization": "Bearer {}".format(DATASETS_SERVER_API_KEY)},
                json=params,
            ) as resp:
                # TODO check here that we have recieved a valid geojson?
                resp_data = io.BytesIO(resp.content)

            filename = "{:02d}_{}.geojson".format(dataset_id, dataset_name)
            content_type = "application/geo+json"
            file_upload = FileStorage(resp_data, filename, content_type=content_type)
            return file_upload
        except ConnectionError:
            raise

    if (params is not None) and (layer_type == "raster"):
        print("Fetching raster dataset " + str(dataset_id))
        # We need to get the dataset info from the db before downloading the files
        # on another server
        file_name = None
        try:
            with requests.post(
                url,
                headers={"Authorization": "Bearer {}".format(DATASETS_SERVER_API_KEY)},
                json=params,
            ) as resp:
                resp_data = resp.json()

                # If there is multiple images to download, download only the 1st one
                # TODO download all the images and combine them - How???
                file_name = resp_data["features"][0]["id"]

            # Create the url to download the file
            raster_url = RASTER_SERVER_URL + str(dataset_id) + "/" + file_name
            try:
                with requests.get(raster_url, stream=True) as resp:
                    resp_data = io.BytesIO(resp.content)
            except ConnectionError:
                raise

            storage_filename = "{:02d}_{}.tiff".format(dataset_id, dataset_name)
            content_type = "image/tiff"
            file_upload = FileStorage(
                resp_data, storage_filename, content_type=content_type
            )
            return file_upload

        except Exception:
            raise
