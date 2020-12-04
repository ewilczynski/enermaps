import logging
from time import time
from typing import List, Optional, Text

import pyproj
import rasterio
from rasterstats import zonal_stats
from shapely.geometry import shape
from shapely.ops import transform

GEOJSON_PROJ = "EPSG:4326"
DEFAULT_STATS = ("min", "max", "mean", "median", "count")

SCALED_STATS = ("min", "max", "mean", "median")


def scale_stat(stats_list, factor):
    """From a list of stats, take the factor into account and
    modify the stats accordingly.
    """
    for stats in stats_list:
        for stat_type in SCALED_STATS:
            non_scaled_stats = stats.get(stat_type)
            if non_scaled_stats:
                stats[stat_type] = non_scaled_stats * factor


def rasterstats(geojson, raster_path, factor, stat_types: Optional[List[Text]] = None):
    """Multiply the rasters values by a factor.

    Rasters are selected from the frontend.
    Factor should be an integrer.
    By default, the indicators are "count min mean max median".
    """
    if not stat_types:
        stat_types = DEFAULT_STATS
    start = time()
    aggregated_stats = []
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        geoshape = shape(geometry)
        with rasterio.open(raster_path) as src:
            project = pyproj.Transformer.from_crs(
                GEOJSON_PROJ, src.crs, always_xy=True
            ).transform
            projected_shape = transform(project, geoshape)
        stats = zonal_stats(
            projected_shape, raster_path, affine=src.transform, stats=stat_types
        )
        # we have a single feature, thus we expose a single stat
        aggregated_stats += stats
    scale_stat(aggregated_stats, factor)
    stat_done = time()

    logging.info("We took {!s} to calculate stats".format(stat_done - start))
    logging.info(stats)
    return aggregated_stats


if __name__ == "__main__":
    val_multiply = rasterstats("selection_shapefile.geojson", "GeoTIFF_test.tif", 2)
