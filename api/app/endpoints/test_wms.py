import io
import json
import os
import shutil
from unittest.mock import Mock, patch

import lxml  # nosec
from lxml import etree  # nosec
from owslib.wms import WebMapService
from PIL import Image

import app.common.xml as xml
from app.common import datasets, path
from app.common.projection import epsg_to_proj4
from app.common.test import BaseApiTest, BaseIntegrationTest
from app.models import storage

GETCAPABILITIES_ARGS = {"service": "WMS", "request": "GetCapabilities"}
WMS_VERSION = "1.3.0"


class BaseWMSTest(BaseApiTest):
    def testFailWhenNoRequestSpecified(self):
        """Try to achieve the WMS without request."""
        response = self.client.get("api/wms", query_string={"service": "WMS"})
        self.assertEqual(response.status, "400 BAD REQUEST", response.data)


class WMSGetCapabilitiesTest(BaseApiTest):
    """Test the get capabilities (a list of all endpoint and layer)"""

    DATASETS = [
        {
            "ds_id": 1,
            "is_raster": True,
            "title": "dataset1",
        },
        {
            "ds_id": 2,
            "is_raster": False,
            "title": "dataset2",
        },
    ]

    PARAMETERS = {
        "end_at": None,
        "parameters": {
            "end_at": None,
            "fields": [],
            "levels": [],
            "is_tiled": False,
            "start_at": None,
            "is_raster": False,
            "variables": [],
            "time_periods": [],
            "temporal_granularity": None,
        },
        "default_parameters": {},
    }

    @classmethod
    def setUpClass(cl):
        """Create the xml schema validator."""
        schema_path = WMSGetCapabilitiesTest.get_testdata_path(
            "WMS_MS_Capabilities_1.3.0.xsd"
        )
        # load additional schemas
        with open(schema_path, "rb") as schema_fd:
            xmlschema = xml.etree_fromstring(schema_fd.read())

        schema_path = WMSGetCapabilitiesTest.get_testdata_path("xml.xsd")
        newimport = lxml.etree.Element(
            "{http://www.w3.org/2001/XMLSchema}import",
            namespace="http://www.w3.org/2001/xml.xsd",
            schemaLocation="file://" + schema_path,
        )
        xmlschema.insert(0, newimport)

        schema_path = WMSGetCapabilitiesTest.get_testdata_path("xlink.xsd")
        newimport = lxml.etree.Element(
            "{http://www.w3.org/2001/XMLSchema}import",
            namespace="http://www.w3.org/1999/xlink.xsd",
            schemaLocation="file://" + schema_path,
        )
        xmlschema.insert(1, newimport)
        cl.schema = etree.XMLSchema(xmlschema)

    @patch(
        "app.common.client.get_dataset_list",
        new=Mock(return_value=DATASETS),
    )
    @patch(
        "app.common.client.get_parameters",
        new=Mock(return_value=datasets.convert(PARAMETERS)),
    )
    def testSucceedWithUppercaseParameters(self):
        """Test that lowercase parameters produces the same result as uppercase
        get parameters
        """
        args = {}
        for k, v in GETCAPABILITIES_ARGS.items():
            args[k.upper()] = v
        response_lower = self.client.get("api/wms", query_string=args)
        response_upper = self.client.get("api/wms", query_string=GETCAPABILITIES_ARGS)
        self.assertEqual(response_lower.data, response_upper.data)
        self._validate_xml_string(response_lower.data)

    def testFailsWhenNoService(self):
        """Test that the call to getcapabilities fails when no service
        parameter is passed as argument
        """
        args = GETCAPABILITIES_ARGS
        del args["service"]
        response = self.client.get("api/wms", query_string={"request": args})
        self.assertEqual(response.status, "400 BAD REQUEST", response.data)

    @patch(
        "app.common.client.get_dataset_list",
        new=Mock(return_value=DATASETS),
    )
    @patch(
        "app.common.client.get_parameters",
        new=Mock(return_value=datasets.convert(PARAMETERS)),
    )
    def testLayerLessCall(self):
        """Test that the call to getCapabilities with no layers defined
        returns an empty list of layers.
        """
        response = self.client.get("api/wms", query_string=GETCAPABILITIES_ARGS)
        self.assertStatusCodeEqual(response, 200)
        root = xml.etree_fromstring(response.data)
        layer_names = root.findall(".//Layer/Layer/Name", root.nsmap)
        self.assertEqual(len(layer_names), 0, "Found a layer, expected none")
        self._validate_xml(root)

    def _validate_xml_string(self, xml_string):
        """Validate a xml schema saved as string based on the xml validator."""
        root = etree.fromstring(xml_string)  # nosec
        self._validate_xml(root)

    def _validate_xml(self, xml_root):
        """Validate a xml schema based on the xml validator."""
        valid = self.schema.validate(xml_root)
        self.assertTrue(valid, self.schema.error_log.filter_from_errors())


class WMSGetMapTest(BaseApiTest):
    """Test the wms GetMap endpoint"""

    TILE_SIZE = (256, 256)
    TILE_PARAMETERS = {
        "service": "WMS",
        "request": "GetMap",
        "layers": "",
        "styles": "",
        "format": "image/png",
        "transparent": "true",
        "version": "1.1.1",
        "width": str(TILE_SIZE[0]),
        "height": str(TILE_SIZE[1]),
        "srs": "EPSG:3857",
        "bbox": (
            "19567.87924100512,6809621.975869781,39135.75848201024,6829189.85511079"
        ),
    }

    def setUp(self):
        super().setUp()

        with self.flask_app.app_context():
            # Copy the vector dataset
            layer_name = path.make_unique_layer_name(path.AREA, "example")
            storage_instance = storage.create(layer_name)

            os.makedirs(storage_instance.get_dir(layer_name))

            shutil.copy(
                self.get_testdata_path("example.geojson"),
                storage_instance.get_geojson_file(layer_name),
            )

            proj_filepath = storage_instance.get_projection_file(layer_name)
            with open(proj_filepath, "w") as fd:
                fd.write(epsg_to_proj4(4326))

            # Copy the raster dataset
            layer_name = path.make_unique_layer_name(path.RASTER, 42, "heat")
            storage_instance = storage.create(layer_name)

            os.makedirs(storage_instance.get_dir(layer_name))

            shutil.copy(
                self.get_testdata_path("hotmaps-cdd_curr_adapted.tif"),
                storage_instance.get_file_path(layer_name, "FID.tif"),
            )

            geometries = {"FID.tif": [[0, 60], [10, 60], [10, 30], [0, 30], [0, 60]]}
            with open(storage_instance.get_geometries_file(layer_name), "w") as f:
                json.dump(geometries, f)

    @patch(
        "app.common.client.get_legend",
        new=Mock(return_value=None),
    )
    def testVectorTileWorkflow(self):
        """Retrieve a vector layer as image from WMS endpoint,
        check if the image has the right size  without being empty.
        """
        args = self.TILE_PARAMETERS
        args["layers"] = path.make_unique_layer_name(path.AREA, "example")

        response = self.client.get("api/wms", query_string=args)
        self.assertStatusCodeEqual(response, 200)
        self.assertGreater(len(response.data), 0)

        image = Image.open(io.BytesIO(response.data))
        self.assertEqual(image.size, self.TILE_SIZE)
        self.assertEqual(image.size, self.TILE_SIZE)
        self.assertEqual(image.format, "PNG")

    @patch(
        "app.common.client.get_legend",
        new=Mock(return_value=None),
    )
    def testVectorTileWorkflowUnknownLayer(self):
        """Retrieve a vector layer as image from WMS endpoint,
        check if the image has the right size  without being empty.
        """
        args = self.TILE_PARAMETERS
        args["layers"] = path.make_unique_layer_name(path.AREA, "unknown")

        response = self.client.get("api/wms", query_string=args)
        self.assertStatusCodeEqual(response, 404)

    @patch(
        "app.common.client.get_legend",
        new=Mock(return_value=None),
    )
    def testRasterTileWorkflow(self):
        """Retrieve a raster layer as image from WMS endpoint,
        then check that the tile request is not empty"""
        args = self.TILE_PARAMETERS
        args["layers"] = path.make_unique_layer_name(path.RASTER, 42, "heat")

        response = self.client.get("api/wms", query_string=args)
        self.assertStatusCodeEqual(response, 200)
        self.assertGreater(len(response.data), 0)

        image = Image.open(io.BytesIO(response.data))
        self.assertEqual(image.size, self.TILE_SIZE)
        self.assertEqual(image.size, self.TILE_SIZE)
        self.assertEqual(image.format, "PNG")

    @patch(
        "app.common.client.get_legend",
        new=Mock(return_value=None),
    )
    def testRasterTileWorkflowUnknownLayer(self):
        """Retrieve a raster layer as image from WMS endpoint,
        then check that the tile request is not empty"""
        args = self.TILE_PARAMETERS
        args["layers"] = path.make_unique_layer_name(path.RASTER, 42, "unknown")

        response = self.client.get("api/wms", query_string=args)
        self.assertStatusCodeEqual(response, 404)


class TestWMSLibCompliance(BaseIntegrationTest):
    def setUp(self, *args, **kwargs):
        """Create the wms endpoint base on the parent self.api_url"""
        super().setUp(*args, **kwargs)
        self.wms_url = self.api_url + "/wms"

    def test_wms_content(self):
        """Verify that the content of the wms can be listed"""
        wms = WebMapService(self.wms_url, version=WMS_VERSION)
        self.assertNotEqual(len(wms.contents), 0)
