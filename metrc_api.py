import os
import requests
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class MetrcAPI:
    BASE_URL = "https://api-missouri.metrc.com"

    def __init__(self):
        self.vendor_api_key = os.getenv("VENDOR_API_KEY")
        self.user_api_key = os.getenv("USER_API_KEY")
        if not self.vendor_api_key or not self.user_api_key:
            raise ValueError("API keys are missing. Ensure they are set in the .env file.")
        self.auth_header = self.get_auth_header()

    def get_auth_header(self):
        credentials = f"{self.vendor_api_key}:{self.user_api_key}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {encoded_credentials}"}

    def get_active_packages(self, license_number):
        """Retrieve active packages for a given license."""
        url = f"{self.BASE_URL}/packages/v1/active"
        params = {"licenseNumber": license_number}
        response = requests.get(url, headers=self.auth_header, params=params)
        response.raise_for_status()
        return response.json()

    def get_testing_results(self, package_id):
        """Retrieve testing results for a specific package."""
        url = f"{self.BASE_URL}/packages/v1/{package_id}/labtests"
        response = requests.get(url, headers=self.auth_header)
        response.raise_for_status()
        return response.json()
