import unittest
import os
import time
import pandas as pd
from arcgis.gis import GIS
from arcgis.features.layer import FeatureLayer, FeatureLayerCollection
from pyparcels.versioning import versioning_utils
from utils import check_arcpy_version, test_order_log, normalize_path

pd.options.mode.copy_on_write = True


class TestFeatureAccess(unittest.TestCase):
    """Test FeatureServer methods"""

    sd_path = None
    vms = None
    gis = None
    services = None
    service_urls = {}
    version_name = None
    base_server_url = None
    parcel_fabric_flc = None

    @classmethod
    def setUpClass(cls):
        test_order_log("TestFeatureAccess")
        cwd = normalize_path()
        cls.sd_path = os.path.join(cwd, "tests", "feature_data")

        # Create Python API GIS object and prepare REST service URL strings
        #  proxy_port=8888, proxy_host="127.0.0.1"
        cls.base_server_url = (
            "https://dev0016752.esri.com/server/rest/services/HCAD_Subset/"
        )
        cls.gis = GIS(
            "https://dev0016752.esri.com/portal",
            "admin",
            "esri.agp"
        )
        endpoints = ["FeatureServer", "VersionManagementServer"]
        cls.service_urls = {url: cls.base_server_url + url for url in endpoints}
        cls.parcel_fabric_flc = FeatureLayerCollection(
            cls.service_urls["FeatureServer"], cls.gis
        )
        cls.vms = cls.parcel_fabric_flc.versions
        cls.tax_service_url = f"{cls.service_urls['FeatureServer']}/15"

    @unittest.skipIf(check_arcpy_version() is False, "Out of date ArcPy version")
    def test_applyedits_small_async(self):
        """Append 250 polygons into a parcel fabric parcel type"""
        fq_version_name = versioning_utils.create_version(self.vms)
        cwd = self.sd_path
        tax_sdf_path = os.path.join(cwd, "WashCoAppend.gdb", "HCADSubset250")
        tax_sdf = pd.DataFrame.spatial.from_featureclass(tax_sdf_path)
        fl = FeatureLayer(self.tax_service_url, self.gis)
        try:
            start = time.perf_counter()
            res = fl.edit_features(
                adds=tax_sdf, gdb_version=fq_version_name, future=True
            )
            elapsed = time.perf_counter() - start
            print("Time to apply 250 polygons:", elapsed)

        except Exception as ex:
            raise ex
        # self.fq_version_name = versioning_utils.create_version(self.vms)
        # self.tax_service_url = f"{self.service_urls['FeatureServer']}/15"

    @unittest.skipIf(check_arcpy_version() is False, "Out of date ArcPy version")
    def test_applyedits_large_async(self):
        """Append 2000 polygons into a parcel fabric parcel type asynchronously"""
        fq_version_name = versioning_utils.create_version(self.vms)
        cwd = self.sd_path
        tax_sdf_path = os.path.join(cwd, "WashCoAppend.gdb", "HCADSubset2k")
        tax_base_df = pd.DataFrame.spatial.from_featureclass(tax_sdf_path)
        tax_sdf = tax_base_df.copy(deep=True)
        fl = FeatureLayer(self.tax_service_url, self.gis)
        try:
            start = time.perf_counter()
            res = fl.edit_features(
                adds=tax_sdf, gdb_version=fq_version_name, future=True
            )
            elapsed = time.perf_counter() - start
            print("Time to apply 2,000 polygons:", elapsed)
        except Exception as ex:
            raise ex

    @unittest.skipIf(check_arcpy_version() is False, "Out of date ArcPy version")
    def test_applyedits_large_noasync(self):
        """Append 2000 polygons into a parcel fabric parcel type synchronously"""
        fq_version_name = versioning_utils.create_version(self.vms)
        cwd = self.sd_path
        tax_sdf_path = os.path.join(cwd, "WashCoAppend.gdb", "HCADSubset2k")
        tax_sdf = pd.DataFrame.spatial.from_featureclass(tax_sdf_path)
        fl = FeatureLayer(self.tax_service_url, self.gis)
        try:
            start = time.perf_counter()
            res = fl.edit_features(
                adds=tax_sdf, gdb_version=fq_version_name, future=False
            )
            elapsed = time.perf_counter() - start
            print("Time to apply 2,000 polygons:", elapsed)
        except Exception as ex:
            raise ex

    def test_update_name_on_curve(self):
        fq_version_name = versioning_utils.create_version(self.vms)
        oids = [13, 14, 15]

        fl = FeatureLayer(self.tax_service_url, self.gis)
        curve_features = fl.query(
            where="OBJECTID IN (13, 14, 15)", gdb_version=fq_version_name
        )
        for i, feature in enumerate(curve_features):
            feature.attributes["Name"] = f"000{oids[i]}"
            update_result = fl.edit_features(
                updates=[feature], gdb_version=fq_version_name, true_curve_client=True
            )
            print(update_result)

        time.sleep(2)

        finished_curve_features = fl.query(
            where="OBJECTID IN (13, 14, 15)", gdb_version=fq_version_name
        )
        for i, feature in enumerate(finished_curve_features):
            self.assertEqual(
                feature.attributes["Name"],
                f"000{oids[i]}",
                f"Incorrect name values for updated feature: Expected: 000{oids[i]}, got {feature.attributes['Name']}",
            )

    def test_query_only_oid(self):
        fl = FeatureLayer(self.tax_service_url, self.gis)
        try:
            curve_features = fl.query(
                where="OBJECTID IN (13, 14, 15)",
                out_fields=["OBJECTID"],
            )
            print(curve_features)
        except Exception as ex:
            print(ex)

    @classmethod
    def tearDownClass(cls):
        versioning_utils.clean_up_versions_by_list(cls.vms, ["pyapi-", "pyparcels"])
