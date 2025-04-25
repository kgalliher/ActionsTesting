import json
import os
from typing import Dict, List, Tuple

import pandas as pd
import tempfile
import functools
import time
from datetime import datetime

import requests
from arcgis import GIS


def normalize_path():
    with open(
        r"./config.json",
        "r",
    ) as conf:
        info = json.load(conf)
        base_path = info["base_path"]
        if os.path.exists(base_path):
            return base_path
    return None


def timer(func):
    """Decorator: Print the runtime of the decorated function

    Args:
      func (function): The function to profile

    Returns:
      The function wrapper
    """

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        """

        Args:
          *args:
          **kwargs:

        Returns:

        """
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"Finished running {func.__name__!r} in {run_time:.4f} seconds.")
        return value

    return wrapper_timer


def dict_to_json_file(path, name, _dict):
    """Write a dict to a json file

    Args:
      path (str): Output dir for new file
      name (str): Name of the new json file
      _dict (dict): The dict to write to the file

    Returns:

    """
    filename = f"{name}_output.json"
    if not path:
        path = tempfile.gettempdir()
    tmp = os.path.join(path, filename)
    j = json.dumps(_dict)
    with open(tmp, "w") as json_file:
        json_file.write(j)


def check_arcpy_version() -> bool:
    try:
        import arcpy

        return True
    except ImportError:
        return False


def generate_layer_queries(layer_ids: list):
    layer_queries_string = "{"
    for i in layer_ids:
        layer_queries_string += (
            f'"{i}":{{"queryOption":"useFilter","useGeometry":true}},'
        )
    layer_queries_string += "}"
    layer_queries_string.replace(":true},}", ":true}}")
    return layer_queries_string.replace(":true},}", ":true}}")


def get_token(server_url, username, password):
    """Generate an ArcGIS Server token

    Args:
      server_url (str): ArcGIS Server admin url
      username (str):
      password (str):

    Returns:
      requests.Models.Response.content value
    """
    my_obj = {"username": username, "password": password, "client": "requestip"}
    x = requests.post(server_url, data=my_obj, verify=False)
    return x.content


def test_order_log(name):
    dt = datetime.now()
    with open(r"C:\temp\test_order.txt", "a") as log:
        log.write(f"{name}:\t{str(dt)}\n")


class ServerLogProcessor:
    """
    Process ArcGIS Server logs into a DataFrame or flat file (.csv, .txt).

    ====================     ====================================================================
    **Argument**             **Description**
    --------------------     --------------------------------------------------------------------
    gis                      Required GIS. The enterprise connection.
    --------------------     --------------------------------------------------------------------
    out_file_path            Optional string. The path and extension of the output file.
    --------------------     --------------------------------------------------------------------
    clean_first              Optional bool.  Should the current log be truncated. Default is False
    --------------------     --------------------------------------------------------------------
    strip_non_parcel         Optional bool.  Filter for parcel fabric operations only. Default is False
    --------------------     --------------------------------------------------------------------
    log_level                Optional string.  Specifies the log level to return ["OFF", "SEVERE",
                                "WARNING", "INFO", "FINE", "VERBOSE", "DEBUG"]. Default is "INFO"
    ====================     ====================================================================

    """

    strip_non_parcel = None
    out_file_path = None

    def __init__(
        self,
        gis,
        out_file_path=None,
        clean_first=False,
        strip_non_parcel=False,
        log_level="INFO",
    ):
        self.gis = gis
        self.out_file_path = out_file_path
        self.clean_first = clean_first
        self.strip_non_parcel = strip_non_parcel
        self.log_level = log_level
        self.server = self.gis.admin.servers.get("HOSTING_SERVER")[0]
        if not self.out_file_path:
            self.out_file_path = f"./ags_log_output_{int(time.time())}.csv"
        if self.server and self.clean_first:
            self.server.logs.clean()

    def process_log_as_csv(self) -> bool:
        logs = self.server.logs.query(start_time=time.time(), level=self.log_level)
        try:
            df = self.process_log_as_dataframe()

            df.to_csv(self.out_file_path, index=False)
            return True

        except Exception as ex:
            print("An error occurred:", repr(ex))
            return False

    def process_log_as_dataframe(self) -> pd.DataFrame:
        logs = self.server.logs.query(start_time=time.time(), level=self.log_level)

        log_messages = logs.get("logMessages", [])
        if len(log_messages) == 0:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(log_messages)
        t = type(df)
        df["date"] = pd.to_datetime(df["time"], unit="ms")
        if self.strip_non_parcel:
            df.dropna(subset=["methodName"])
            df = df.loc[df.methodName.str.startswith("ParcelOperation::")]
        return df

    def get_operation_total_time(self, parcel_operation) -> Tuple:
        df = self.process_log_as_dataframe()[["message", "methodName"]]
        out_times = {}

        total_time_q = df.loc[
            (df["message"].str.contains(parcel_operation))
            & (df["message"].str.contains("Total Time"))
        ]
        time_str = ":".join(total_time_q.iloc[0].message.split(":")[-3:])

        total_time = datetime.strptime(time_str, "%H:%M:%S.%f")
        return parcel_operation, total_time

    def all_operations_total_time(self) -> Dict[str, datetime]:
        operation_times = {}
        df = self.process_log_as_dataframe()[["message", "methodName"]]
        logged_operations = [o.split("::")[1] for o in df["methodName"].unique()]

        for lo in logged_operations:
            operation = self.get_operation_total_time(lo)
            operation_times[operation[0]] = operation[1]
        return operation_times

    def clean_server_logs(self):
        self.server.logs.clean()
        assert self.process_log_as_dataframe().empty, "Log entries not truncated."
