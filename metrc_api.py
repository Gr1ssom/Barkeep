import os
import requests
import base64
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging to log errors to output.txt
logging.basicConfig(filename='output.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


class MetrcAPI:
    BASE_URL = "https://api-mo.metrc.com"

    def __init__(self):
        self.vendor_api_key = os.getenv("VENDOR_API_KEY")
        self.user_api_key = os.getenv("USER_API_KEY")
        if not self.vendor_api_key or not self.user_api_key:
            raise ValueError("API keys are missing. Ensure they are set in the .env file.")
        self.auth_header = self.get_auth_header()

    def get_auth_header(self):
        credentials = f"{self.vendor_api_key}:{self.user_api_key}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_active_packages(self, license_number, partial_tag=None):
        url = f"{self.BASE_URL}/packages/v2/active"
        params = {"licenseNumber": license_number}
        response = self._make_request(url, params)

        # Validate response and filter packages locally
        if isinstance(response, dict) and "Data" in response:
            active_packages = response["Data"]

            # Filter by LabTestingState and partial tag
            filtered_packages = [
                pkg for pkg in active_packages
                if pkg.get("LabTestingState") == "TestPassed" and (partial_tag in pkg.get("Label", ""))
            ]

            logging.debug(f"Filtered packages: {filtered_packages}")
            return filtered_packages

        raise ValueError("Unexpected response format: 'Data' field missing or invalid.")

    def get_lab_test_results(self, package_id, license_number):
        url = f"{self.BASE_URL}/labtests/v2/results"
        params = {"packageId": package_id, "licenseNumber": license_number}

        # Log the request details for debugging
        logging.debug(f"Fetching lab test results with params: {params}")

        return self._make_request(url, params)

    def _make_request(self, url, params):
        try:
            response = requests.get(url, headers=self.auth_header, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Log response content for detailed debugging
            error_message = f"HTTP Error: {e}\nResponse: {response.text if response else 'No response body'}"
            logging.error(error_message)
            raise ValueError(error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
            logging.error(error_message)
            raise ValueError(error_message)
