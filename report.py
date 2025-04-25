import os
import json
import shutil
from datetime import datetime


class TestReport:
    results_json = None

    def __init__(self, base_report_dir):
        self.base_report_dir = base_report_dir
        t = datetime.now()
        self.date_stamp = t.strftime("%Y_%m_%d_%I_%M_%S")
        self.out_folder = self.create_report_dir()
        self.xmlfile = os.path.join(self.out_folder, "results.xml")
        self.jsonfile = os.path.join(self.out_folder, "results.json")

    def get_test_result_url(self):
        return f"http://kgalliher.esri.com:85/pyapi_results/pyapi_results_{self.date_stamp}/results.html"

    def set_results_json(self, results_json):
        self.results_json = results_json

    def create_report_dir(self):
        new_folder = os.path.join(
            self.base_report_dir, f"pyapi_results_{self.date_stamp}"
        )
        os.mkdir(new_folder)
        return new_folder

    def parse_results_to_json(self):
        with open(self.jsonfile, "w") as j:
            j.write(json.dumps(self.results_json))

    def create_high_level_report(self):
        self.parse_results_to_json()
        shutil.copy(os.path.join(self.base_report_dir, "results.html"), self.out_folder)
