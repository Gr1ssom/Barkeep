import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt

# Load environment variables from .env
load_dotenv()

# Set up logging to a file called debug.log with rotation
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# File handler with rotation
file_handler = RotatingFileHandler("debug.log", maxBytes=5 * 1024 * 1024, backupCount=2)  # 5MB per file
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

API_BASE = "https://api-mo.metrc.com"

# Retrieve API credentials from environment variables
API_KEY = os.getenv("VENDOR_API_KEY")
USER_KEY = os.getenv("USER_API_KEY")

# Validate API credentials
if not API_KEY or not USER_KEY:
    logger.critical("API_KEY or USER_KEY not set in environment variables.")
    raise EnvironmentError("API credentials are not set.")

# Prefix mappings (if applicable)
PREFIXES = {
    "MAN000035": "1A40C03000043950000",
    "CUL000032": "1A40C030000332D0000"
}

# Custom exception for API errors
class MetrcAPIError(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

# Initialize a session for connection pooling
session = requests.Session()
session.auth = HTTPBasicAuth(API_KEY, USER_KEY)

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(5))
def make_api_request(endpoint: str, params: dict = None) -> requests.Response:
    """
    Make a GET API request with retry logic.
    Retries on failures (network-related issues) with exponential backoff.

    Parameters:
        endpoint (str): The API endpoint URL.
        params (dict, optional): Query parameters for the GET request.

    Returns:
        requests.Response: The response object.

    Raises:
        requests.RequestException: If the request fails after retries.
    """
    try:
        logger.debug("Making GET request to endpoint: %s with params: %s", endpoint, params)
        response = session.get(endpoint, params=params, timeout=10)  # Added timeout for better control
        response.raise_for_status()
        logger.debug("Received response with status code: %s", response.status_code)
        return response
    except requests.RequestException as e:
        logger.error("GET request to %s failed: %s", endpoint, str(e))
        raise e

def get_package_id(license_code: str, full_label: str) -> dict:
    """
    Fetches package details based on license number and package label.

    Parameters:
        license_code (str): The license number.
        full_label (str): The full label of the package.

    Returns:
        dict: Contains success status and package details or error message.
    """
    endpoint = f"{API_BASE}/packages/v2/{full_label}"
    params = {"licenseNumber": license_code}
    logger.info("Requesting package details from: %s with params: %s", endpoint, params)

    try:
        response = make_api_request(endpoint, params=params)
    except requests.RequestException as e:
        logger.exception("Network error while contacting Metrc API for package details: %s", e)
        return {"success": False, "error": "Network error"}

    try:
        package_data = response.json()
        logger.debug("Package Data JSON: %s", package_data)
    except ValueError:
        logger.error("Invalid JSON response for packageLabel=%s: %s", full_label, response.text)
        return {"success": False, "error": "Invalid JSON response"}

    if isinstance(package_data, dict):
        package_id = package_data.get("Id")
        product_name = package_data.get("Item", {}).get("Name", "") or full_label
        source_package_label = package_data.get("SourcePackageLabel", "")
        source_package_id = package_data.get("SourcePackageId")
        number_of_doses = package_data.get("NumberOfDoses", "N/A")
        ingredients_list = package_data.get("IngredientsList", "N/A")  # Assuming this field exists

        # If we have a source package id but no label, fetch it
        if not source_package_label and source_package_id:
            source_package_label = get_source_package_label(license_code, source_package_id)

        if package_id:
            logger.debug("Found packageId=%s for label=%s", package_id, full_label)
            return {
                "success": True,
                "package_id": package_id,
                "product_name": product_name,
                "source_package_label": source_package_label or "N/A",
                "number_of_doses": number_of_doses,
                "ingredients_list": ingredients_list
            }
        else:
            logger.error("packageId not found in the response for label=%s", full_label)
            return {"success": False, "error": "packageId not found"}
    else:
        logger.error("Unexpected JSON structure for package details: %s", package_data)
        return {"success": False, "error": "Unexpected JSON structure"}

def get_source_package_label(license_code: str, source_package_id: int) -> str:
    """
    Retrieves the label of a source package given its ID.

    Parameters:
        license_code (str): The license number.
        source_package_id (int): The ID of the source package.

    Returns:
        str: The label of the source package or "N/A" if not found.
    """
    endpoint = f"{API_BASE}/packages/v2/{source_package_id}"
    params = {"licenseNumber": license_code}
    logger.info("Requesting source package details from: %s with params: %s", endpoint, params)

    try:
        response = make_api_request(endpoint, params=params)
    except requests.RequestException as e:
        logger.exception("Network error while contacting Metrc API for source package details: %s", e)
        return "N/A"

    try:
        data = response.json()
        label = data.get("Label", "N/A")
        logger.debug("Source package label: %s", label)
        return label
    except ValueError:
        logger.error("Invalid JSON when fetching source package: %s", response.text)
        return "N/A"

def get_test_results(license_code: str, package_id: int, page_size: int = 20) -> dict:
    """
    Fetches lab test results associated with a specific package.

    Parameters:
        license_code (str): The license number.
        package_id (int): The ID of the package.
        page_size (int, optional): Number of records per page. Defaults to 20.

    Returns:
        dict: Contains success status and test results data or error message.
    """
    all_test_results = []
    page_number = 1
    total_pages = 1

    while page_number <= total_pages:
        endpoint = f"{API_BASE}/labtests/v2/results"
        params = {
            "licenseNumber": license_code,
            "packageId": package_id,
            "pageNumber": page_number,
            "pageSize": page_size
        }
        logger.info("Requesting test results from: %s with params: %s", endpoint, params)

        try:
            response = make_api_request(endpoint, params=params)
        except requests.RequestException as e:
            logger.exception("Network error while contacting Metrc API for test results: %s", e)
            return {"success": False, "error": "Network error"}

        try:
            test_results = response.json()
            logger.debug("Test Results JSON: %s", test_results)
        except ValueError:
            logger.error("Invalid JSON response for packageId=%s: %s", package_id, response.text)
            return {"success": False, "error": "Invalid JSON response"}

        if isinstance(test_results, dict):
            data = test_results.get("Data", [])
            all_test_results.extend(data)
            total_pages = test_results.get("TotalPages", 1)
        elif isinstance(test_results, list):
            all_test_results.extend(test_results)
            total_pages = 1
        else:
            logger.error("Unexpected JSON structure for test results: %s", test_results)
            return {"success": False, "error": "Unexpected JSON structure"}

        logger.info("Fetched page %d/%d with %d test results.", page_number, total_pages, len(data))
        page_number += 1

    logger.info("Total test results fetched: %d", len(all_test_results))
    return {"success": True, "data": all_test_results}
