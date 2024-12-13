import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging to a file called debug.log with rotation
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler("debug.log", maxBytes=5*1024*1024, backupCount=2)  # 5MB per file
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

API_BASE = "https://api-mo.metrc.com"

API_KEY = os.getenv("VENDOR_API_KEY")
USER_KEY = os.getenv("USER_API_KEY")

PREFIXES = {
    "MAN000035": "1A40C03000043950000",
    "CUL000032": "1A40C030000332D0000"
}

def get_package_id(license_code: str, full_label: str):
    endpoint = f"{API_BASE}/packages/v2/{full_label}?licenseNumber={license_code}"
    logging.info("Requesting package details from: %s", endpoint)

    try:
        response = requests.get(endpoint, auth=HTTPBasicAuth(API_KEY, USER_KEY))
    except requests.RequestException as e:
        logging.exception("Network error while contacting Metrc API for package details: %s", e)
        return {"success": False, "error": "Network error"}

    if response.status_code == 200:
        logging.debug("Successful response received for packageLabel=%s", full_label)
        try:
            package_data = response.json()
            logging.debug("Package Data JSON: %s", package_data)
            if isinstance(package_data, dict):
                package_id = package_data.get("Id")
                product_name = package_data.get("Item", {}).get("Name", "") or full_label
                source_package_label = package_data.get("SourcePackageLabel", "")
                source_package_id = package_data.get("SourcePackageId")

                # If we have a source package id but no label, fetch it
                if not source_package_label and source_package_id:
                    source_package_label = get_source_package_label(license_code, source_package_id)

                if package_id:
                    logging.debug("Found packageId=%s for label=%s", package_id, full_label)
                    return {
                        "success": True,
                        "package_id": package_id,
                        "product_name": product_name,
                        "source_package_label": source_package_label or "N/A"
                    }
                else:
                    logging.error("packageId not found in the response for label=%s", full_label)
                    return {"success": False, "error": "packageId not found"}
            else:
                logging.error("Unexpected JSON structure for package details: %s", package_data)
                return {"success": False, "error": "Unexpected JSON structure"}
        except ValueError:
            logging.error("Invalid JSON response for packageLabel=%s: %s", full_label, response.text)
            return {"success": False, "error": "Invalid JSON response"}
    elif response.status_code == 401:
        logging.error("Unauthorized access for packageLabel=%s. Check API credentials.", full_label)
        return {"success": False, "error": "Unauthorized"}
    else:
        logging.error(
            "Error %d from Metrc API for packageLabel=%s: %s", 
            response.status_code, full_label, response.text
        )
        return {"success": False, "error": f"HTTP {response.status_code}"}

def get_source_package_label(license_code: str, source_package_id: int):
    endpoint = f"{API_BASE}/packages/v2/{source_package_id}?licenseNumber={license_code}"
    logging.info("Requesting source package details from: %s", endpoint)

    try:
        response = requests.get(endpoint, auth=HTTPBasicAuth(API_KEY, USER_KEY))
    except requests.RequestException as e:
        logging.exception("Network error while contacting Metrc API for source package details: %s", e)
        return "N/A"

    if response.status_code == 200:
        try:
            data = response.json()
            return data.get("Label", "N/A")
        except ValueError:
            logging.error("Invalid JSON when fetching source package: %s", response.text)
            return "N/A"
    else:
        logging.error("Failed to fetch source package details (HTTP %d): %s", response.status_code, response.text)
        return "N/A"

def get_test_results(license_code: str, package_id: int, page_size=20):
    all_test_results = []
    page_number = 1
    total_pages = 1

    while page_number <= total_pages:
        endpoint = (
            f"{API_BASE}/labtests/v2/results?"
            f"licenseNumber={license_code}&"
            f"packageId={package_id}&"
            f"pageNumber={page_number}&"
            f"pageSize={page_size}"
        )
        logging.info("Requesting test results from: %s", endpoint)

        try:
            response = requests.get(endpoint, auth=HTTPBasicAuth(API_KEY, USER_KEY))
        except requests.RequestException as e:
            logging.exception("Network error while contacting Metrc API for test results: %s", e)
            return {"success": False, "error": "Network error"}

        if response.status_code == 200:
            try:
                test_results = response.json()
                if isinstance(test_results, dict) and "Data" in test_results:
                    data = test_results["Data"]
                    all_test_results.extend(data)
                    total_pages = test_results.get("TotalPages", 1)
                elif isinstance(test_results, list):
                    all_test_results.extend(test_results)
                    total_pages = 1
                else:
                    logging.error("Unexpected JSON structure for test results: %s", test_results)
                    return {"success": False, "error": "Unexpected JSON structure"}
            except ValueError:
                logging.error("Invalid JSON response for packageId=%s: %s", package_id, response.text)
                return {"success": False, "error": "Invalid JSON response"}
        elif response.status_code == 401:
            logging.error("Unauthorized access for packageId=%s.", package_id)
            return {"success": False, "error": "Unauthorized"}
        elif response.status_code == 400:
            logging.error("Bad request for packageId=%s: %s", package_id, response.text)
            return {"success": False, "error": response.text}
        else:
            logging.error(
                "Error %d from Metrc API for packageId=%s: %s", 
                response.status_code, package_id, response.text
            )
            return {"success": False, "error": f"HTTP {response.status_code}"}
        
        page_number += 1

    logging.info("Total test results fetched: %s", len(all_test_results))
    return {"success": True, "data": all_test_results}
