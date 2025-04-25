import datetime
import json
import shutil
import os
import time

from pyparcels.utils.utils import get_enterprise_build_info

from report import TestReport
from HtmlTestRunner import HTMLTestRunner

# from pyunitreport import HTMLTestRunner
from unittest import TestLoader, TestSuite
import sys

sys.path.append("../notifier")
import notifier


def create_temp_dir(temp_path):
    """Create a folder to store output test results
    :param temp_path: The root path of the new folder to create
    :return: A folder with a unique timestamp inside the temp_path

    create_temp_dir(r"C:\\temp")
    "C:\\temp\\pyapi_results_temp_2021_08_19_09_17_39"
    """
    t = datetime.datetime.now()
    date_stamp = t.strftime("temp_%Y_%m_%d_%I_%M_%S")
    new_folder = os.path.join(temp_path, f"pyapi_results_{date_stamp}")
    os.mkdir(new_folder)
    return new_folder


def get_outcomes(html_runner_result):
    """Pull out the individual test results by their type

    :param html_runner_result: TestResult (HTMLTestRunner)
    :return: Dict(str:list, str:list, str:list, str:list, int)
    """
    outcomes = {
        "skips": html_runner_result.skipped,
        "errors": html_runner_result.errors,
        "failures": html_runner_result.failures,
        "successes": html_runner_result.successes,
        "total_tests": html_runner_result.testsRun,
    }
    return outcomes


def create_high_level_results(html_runner_result, temp_dir_path):
    """Generate the sum of test outcomes, percent pass/fail from full
    test run. Append the test result file with new file path for web server.

    :param html_runner_result: TestResult (HTMLTestRunner)
    :param temp_dir_path: Base path of web server folder
    :return: Dict
    """
    skips, errors, failures, successes, total_tests = get_outcomes(
        html_runner_result
    ).values()
    timestamp = datetime.datetime.now()
    date_stamp = timestamp.strftime("%m/%d/%Y, %H:%M:%S")
    num_fail_err = sum([len(errors), len(failures)])
    # tests_run = html_runner_result.testsRun - len(skips)
    tests_run = total_tests - len(skips)

    if num_fail_err <= 0:
        pct_pass = 100
    elif num_fail_err > 0 >= tests_run:
        pct_pass = 0
    else:
        pct_pass = 100 - ((num_fail_err / tests_run) * 100)

    results = {
        "time": date_stamp,
        "counts": {
            "total_tests": total_tests,
            "skipped": len(skips),
            "errors": len(errors),
            "failures": len(failures),
            "successes": len(successes),
            "pct": round(pct_pass, 2),
        },
        "test_results": test_result_info(html_runner_result, temp_dir_path),
    }
    return results


def formatted_high_level_results(results, results_url, title_info=""):
    """Generate an html string containing test result metrics and link to final test results.
    This is the email message

    :param results (Dict): The high-level test results
    :param results_url (str): The URL to the current test results web page

    :return: str: The html string to display results
    """
    html = f"<h2>Python API Test Results<h2><p>{title_info}</p><p>{results['time']}</p>"
    html += "<h3>Result counts</h3><table style=padding-left:30px;><thead><th>Metric</th><th>Results</th></thead><tbody>"
    html += f"<tr><td>Total Tests</td><td>{results['counts'].get('total_tests', 'error')}</td></tr>"
    html += (
        f"<tr><td>Pass</td><td>{results['counts'].get('successes', 'error')}</td></tr>"
    )
    html += (
        f"<tr><td>Fail</td><td>{results['counts'].get('failures', 'error')}</td></tr>"
    )
    html += (
        f"<tr><td>Error</td><td>{results['counts'].get('errors', 'error')}</td></tr>"
    )
    html += (
        f"<tr><td>Skip</td><td>{results['counts'].get('skipped', 'error')}</td></tr>"
    )
    html += (
        f"<tr><td>Percentage</td><td>{results['counts'].get('pct', 'error')}%</td></tr>"
    )
    html += "</tbody></table>"
    html += f"<br /><p><a href='{results_url}'>View full report</a></p>"
    return html


def test_result_info(html_runner_result, temp_dir_path):
    """Parse each test result type per test class and the
    resulting test result html files.

    :param html_runner_result: TestResult (HTMLTestRunner)
    :param temp_dir_path: Base path of web server folder
    :return: Dict
    """
    # each outcome is a list. Get the result lists and merge them together.
    skips, errors, failures, successes, total_tests = get_outcomes(
        html_runner_result
    ).values()
    results = skips + errors + failures + successes
    formatted_report_files = format_report_filenames(
        html_runner_result.report_files, temp_dir_path=temp_dir_path
    )
    class_names = set()
    test_result_dict = {}
    out_test_results = []
    # Get a set of class names
    for result in results:
        class_name = result.test_name.split(".")[1]
        class_names.add(class_name)

    # Set up a dict for each class name with empty result stats
    for cn in class_names:
        test_result_dict = {
            "test_class": cn,
            "num_tests": 0,
            "successes": 0,
            "failures": 0,
            "errors": 0,
            "skips": 0,
            "file": None,
        }

        # Calculate the sums of test result outcomes
        for res in results:
            class_name = res.test_name.split(".")[1]
            if class_name == cn:
                if res.outcome == 0:
                    test_result_dict["successes"] += 1
                if res.outcome == 1:
                    test_result_dict["failures"] += 1
                if res.outcome == 2:
                    test_result_dict["errors"] += 1
                if res.outcome == 3:
                    test_result_dict["skips"] += 1
                # Associate the test result html file with its class name
                test_result_dict["file"] = [
                    f for f in formatted_report_files if class_name in f
                ]
            if class_name == "suite":
                if test_result_dict.get("file", None):
                    if len(test_result_dict["file"]) == 0:
                        if len(formatted_report_files) > 0:
                            test_result_dict["file"].append(formatted_report_files[0])
            else:
                print("Catching suite errors didn't work")

        out_test_results.append(test_result_dict)
    return out_test_results


def format_report_filenames(file_paths_to_change, temp_dir_path):
    """Prepare the test result html file paths.  Append the path
    of the final destination on the web server
    """
    new_paths = []
    cwd = os.getcwd()
    for file in file_paths_to_change:
        path_part_to_replace = os.path.join(cwd, temp_dir_path)
        filename_string = file.replace(path_part_to_replace, "result_out")
        if os.path.exists(file) and " (" in filename_string:
            os.rename(file, file.replace(" (", "_"))
            filename_string = filename_string.replace(" (", "_")

        new_paths.append(filename_string)
    return new_paths


def remove_temp_files(temp_path):
    """Remove folders and their files from the temp output path
    :param temp_path: The root folder containing files to delete

    Note: Skips the root path passed in. Only deletes files inside temp_path
    """
    for root, d, file in os.walk(temp_path):
        try:
            if root == temp_path:
                continue
            shutil.rmtree(root, ignore_errors=False)
        except OSError as ex:
            print(f"Error deleting {root}:\n{ex}")
        except Exception as gex:
            print(f"General error deleting directory: {gex}")


if __name__ == "__main__":
    from pathlib import Path

    # Use this variable when debugging in IDE
    # 'test_*' runs all test classes starting with 'test_'
    # 'test_TransferParcels' runs all tests in the test_TransferParcels class only
    test_class = "test_*"

    # Create file locations and labels
    start_time = time.time()
    cwd = os.getcwd()
    test_loc = os.path.join(cwd, "tests")
    report_title = "Parcel Fabric PyAPI"
    additional_info = ""
    if len(sys.argv) > 1:
        additional_info = sys.argv[1]
        report_title = f"{report_title} {additional_info}"
    if len(sys.argv) > 2:
        test_class = sys.argv[2]

    web_server_path = r"\\kgalliher\\c$\inetpub\wwwroot\KGUtils\wwwroot\pyapi_results"
    report = TestReport(web_server_path)
    temp_dir = create_temp_dir(r"result_out")
    out_dir = report.out_folder

    # Clear out test order file
    with open(r"C:\temp\test_order.txt", "w"):
        pass
    with open("config.json", "r") as conf:
        info = json.load(conf)
        emails = info["email_addresses"]

    # Prep and run tests
    tests = TestLoader().discover(test_loc, f"{test_class}.py")
    suite = TestSuite(tests)

    # base HTMLTestRunner call
    runner = HTMLTestRunner(
        report_title=report_title, add_timestamp=True, output=temp_dir
    )

    test_results = runner.run(suite)
    result_stats = create_high_level_results(test_results, temp_dir)

    # Prep high level report info and transfer results to web server
    report.set_results_json(result_stats)
    report.create_high_level_report()

    shutil.copytree(temp_dir, os.path.join(out_dir, "result_out"))
    remove_temp_files("result_out")
    end_time = time.time()
    total_time = (end_time - start_time) / 60
    # Notify via email
    enterprise_build_num = "AGOL"
    if not test_class.startswith("agol"):
        portal_info = get_enterprise_build_info(
            "https://dev0016752.esri.com/portal/", "admin", "esri.agp"
        )
        enterprise_build_num = portal_info["enterpriseBuild"]

    report_title = f"{report_title}: Build: {enterprise_build_num}"
    mail_dict = {
        "sender": "kgalliher@esri.com",
        "recipients": emails,
        "subject": f"Python API Test Results - {additional_info}: {total_time:.2f} mins",
        "body": formatted_high_level_results(
            result_stats, report.get_test_result_url(), report_title
        ),
    }
    mailer = notifier.Emailer(mail_dict)
    mailer.send_mail()
