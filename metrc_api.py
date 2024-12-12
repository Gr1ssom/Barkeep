import os
import requests
import base64
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(filename='metrc_debug.log', level=logging.DEBUG)

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

    def get_active_packages(self, license_number):
        url = f"{self.BASE_URL}/packages/v2/active"
        params = {"licenseNumber": license_number}
        response = self._make_request(url, params)

        # Debugging: Log raw response structure
        logging.debug(f"Raw Active Packages Response: {response}")

        # Extract the 'Data' field, which contains the list of active packages
        if isinstance(response, dict) and "Data" in response:
            return response["Data"]

        raise ValueError("Unexpected response format: 'Data' field missing.")

    def get_lab_test_results(self, package_id, license_number):
        url = f"{self.BASE_URL}/labtests/v2/results"
        params = {"packageId": package_id, "licenseNumber": license_number}

        # Debugging: Log package and license info
        logging.debug(f"Fetching lab test results for packageId: {package_id}, licenseNumber: {license_number}")

        return self._make_request(url, params)

    def _make_request(self, url, params):
        try:
            # Debugging: Log request details
            logging.debug(f"Making API request to: {url} with params: {params}")

            response = requests.get(url, headers=self.auth_header, params=params)
            response.raise_for_status()
            return response.json()  # Always parse as JSON
        except requests.exceptions.HTTPError as e:
            # Debugging: Log response content on error
            logging.error(f"HTTP Error: {e}, Response Content: {response.text}")
            raise ValueError(f"HTTP Error: {e}")
        except ValueError:
            raise ValueError("Invalid JSON response from API.")
