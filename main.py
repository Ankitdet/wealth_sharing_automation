import http.client
import json
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import csv
from pathlib import Path
from datetime import datetime
import random
import time
import os
from dotenv import load_dotenv
from itertools import cycle

load_dotenv()

DOMAINS = cycle([
    "https://dsj77.net",
    "https://dsj44.com",
    "https://dsj35.com",
])

def generate_browser_profiles(n=50):
    desktop_platforms = [
        ("Windows", "Windows NT 10.0; Win64; x64"),
        ("Windows", "Windows NT 11.0; Win64; x64"),
        ("Windows", "Windows NT 6.1; Win64; x64"),
        ("Windows", "Windows NT 6.3; Win64; x64"),
        ("Windows", "Windows NT 10.0; WOW64"),
        ("macOS", "Macintosh; Intel Mac OS X 11_7"),
        ("macOS", "Macintosh; Intel Mac OS X 12_6"),
        ("macOS", "Macintosh; Intel Mac OS X 13_5"),
        ("macOS", "Macintosh; Intel Mac OS X 14_0"),
        ("macOS", "Macintosh; Apple Silicon Mac OS X 14_1"),
        ("Linux", "X11; Linux x86_64"),
        ("Linux", "X11; Ubuntu; Linux x86_64"),
        ("Linux", "X11; Fedora; Linux x86_64"),
        ("Linux", "X11; Debian; Linux x86_64"),
        ("Linux", "X11; Arch Linux; Linux x86_64"),
        ("Linux", "X11; Linux armv8l"),
    ]

    mobile_platforms = [
        ("iPhone", "iPhone; CPU iPhone OS 15_7 like Mac OS X"),
        ("iPhone", "iPhone; CPU iPhone OS 16_5 like Mac OS X"),
        ("iPhone", "iPhone; CPU iPhone OS 17_0 like Mac OS X"),
        ("iPhone", "iPhone; CPU iPhone OS 17_3 like Mac OS X"),
        ("iPad", "iPad; CPU OS 15_8 like Mac OS X"),
        ("iPad", "iPad; CPU OS 16_6 like Mac OS X"),
        ("iPad", "iPad; CPU OS 17_0 like Mac OS X"),
        ("Android", "Linux; Android 10; SM-A515F"),
        ("Android", "Linux; Android 11; SM-G991B"),
        ("Android", "Linux; Android 12; Pixel 7"),
        ("Android", "Linux; Android 13; Redmi Note 12"),
        ("Android", "Linux; Android 14; Samsung Galaxy S23"),
        ("Android", "Linux; Android 14; Pixel 8"),
        ("Android", "Linux; Android 13; OnePlus 11"),
        ("Android", "Linux; Android 12; Mi 11X"),
        ("Android", "Linux; Android 11; Nokia G21"),
    ]

    platforms = desktop_platforms + mobile_platforms

    profiles = []
    for _ in range(n):
        chrome_ver = random.randint(114, 124)
        safari_ver = random.randint(15, 17)

        platform_name, platform_ua = random.choice(platforms)

        if platform_name in ("iPhone", "Android", "iPad"):
            ua = (
                f"Mozilla/5.0 ({platform_ua}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{safari_ver}.0 Mobile Safari/605.1.15"
            )
            sec_ua = '"Not(A:Brand";v="8", "Safari";v="17"'
            mobile = "?1"
        else:
            engine = random.choice(["Chrome", "Edg"])
            ua = (
                f"Mozilla/5.0 ({platform_ua}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"{engine}/{chrome_ver}.0.0.0 Safari/537.36"
            )
            sec_ua = (
                f'"Chromium";v="{chrome_ver}", '
                f'"Not(A:Brand";v="8", '
                f'"{engine}";v="{chrome_ver}"'
            )
            mobile = "?0"

        profiles.append(
            {
                "user-agent": ua,
                "sec-ch-ua": sec_ua,
                "sec-ch-ua-platform": f'"{platform_name}"',
                "sec-ch-ua-mobile": mobile,
            }
        )

    return profiles

class HeaderRotator:
    def __init__(self, size=50):
        self.pool = generate_browser_profiles(size)
        random.shuffle(self.pool)
        self.index = 0

    def next(self):
        header = self.pool[self.index]
        self.index += 1

        if self.index >= len(self.pool):
            random.shuffle(self.pool)
            self.index = 0

        return header


@dataclass
class APIConfig:
    """Configuration for API client"""
    base_url: str = os.getenv("API_BASE_URL", "api.ddjea.com")
    origin: str = os.getenv("ORIGIN", "https://dsj44.com")
    referer: str = os.getenv("REFERER", "https://dsj44.com/")
    request_domain: str = os.getenv("REQUEST_DOMAIN", "https://dsj44.com/pc/#/")
    app_version: str = os.getenv("APP_VERSION", "P2.9.3")
    timezone: str = os.getenv("TIMEZONE", "+8")
    language: str = os.getenv("LANGUAGE", "ENGLISH")
    referral_code: str = os.getenv("REFERRAL_CODE", "TESTSET")


class BGolAPIClient:
    """Client for interacting with bgol.pro API"""

    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize the API client

        Args:
            config: Optional APIConfig object. Uses defaults if not provided.
        """
        self.config = config or APIConfig()
        self.token: Optional[str] = None
        self.referral_code = self.config.referral_code
        self.header_rotator = HeaderRotator(50)

    def _get_common_headers(self) -> Dict[str, str]:
        browser = self.header_rotator.next()
        base = next(DOMAINS)
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "app-analog": "false",
            "app-client-timezone": self.config.timezone,
            "app-version": self.config.app_version,
            "aws-check": "true",
            "content-type": "application/json;charset=UTF-8",
            "origin": base,
            "priority": "u=1, i",
            "referer": f"{base}/",
            "request-domain":  f"{base}/pc/#/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "set-aws": "true",
            "set-language": self.config.language,
            "x-requested-with": "XMLHttpRequest",
            "user-agent": browser["user-agent"],
            "sec-ch-ua": browser["sec-ch-ua"],
            "sec-ch-ua-platform": browser["sec-ch-ua-platform"],
            "sec-ch-ua-mobile": browser["sec-ch-ua-mobile"],
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        body = json.dumps(payload) if payload else None
        for attempt in range(max_retries):
            # 🔁 Rotate headers every attempt
            headers = self._get_common_headers()
            if additional_headers:
                headers.update(additional_headers)
            conn = http.client.HTTPSConnection(self.config.base_url, timeout=20)
            try:
                conn.request(method, endpoint, body, headers)
                response = conn.getresponse()
                raw_data = response.read()
                text_data = raw_data.decode("utf-8", errors="ignore")

                # ✅ Success
                if response.status in (200, 201):
                    try:
                        return json.loads(text_data)
                    except json.JSONDecodeError:
                        raise Exception(f"Invalid JSON response: {text_data}")

                # 🚦 Rate limited
                if response.status == 429:
                    wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"⚠️ 429 Too Many Requests. Rotating UA. Sleeping {wait:.1f}s...")
                    time.sleep(wait)
                    continue

                # 🛑 Likely fingerprint / auth block
                if response.status in (401, 403):
                    wait = random.uniform(2.0, 4.0)
                    print(f"⚠️ {response.status} Blocked. Rotating UA. Sleeping {wait:.1f}s...")
                    time.sleep(wait)
                    continue

                # ❌ Other errors (don’t retry)
                raise Exception(
                    f"API request failed with status {response.status}: {text_data}"
                )

            except (http.client.HTTPException, TimeoutError) as e:
                wait = (2 ** attempt) + random.uniform(1.0, 2.0)
                print(f"⚠️ Network error: {e}. Retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue

            finally:
                conn.close()

        raise Exception("Max retries exceeded (rotating UA each attempt)")

    def get_show_all_followed(self) -> Optional[str]:
        if not self.token:
            raise Exception("Not authenticated. Please login first.")
        payload = {
            "pageNum": 0,
            "pageSize": 5,
            "isFinish": False
        }

        additional_headers = {"app-login-token": self.token}

        response = self._make_request(
            "POST",
            "/api/app/second/share/user/list",
            payload,
            additional_headers,
        )
        show_all = response.get("data", {}).get("showAllFollowed", [])
        if show_all:
            return show_all[0]
        return None

    def login(self, email: str, password: str = "", is_validator: bool = True) -> str:
        """
        Authenticate user and retrieve access token

        Args:
            email: User email address
            password: User password (empty string by default)
            is_validator: Whether the user is a validator

        Returns:
            Authentication token

        Raises:
            Exception: If login fails or token is not in response
        """
        payload = {"password": password, "isValidator": is_validator, "email": email}

        response = self._make_request("POST", "/api/app/user/login", payload)

        token = response.get("data")
        if not token:
            raise Exception(f"Login failed: No token in response. Response: {response}")

        self.token = token
        return token

    def follow_share(self, share_id: str) -> Dict[str, Any]:
        """
        Follow a shared user by shareId

        Args:
            share_id: Share ID to follow

        Returns:
            API response as dictionary

        Raises:
            Exception: If not authenticated or request fails
        """
        if not self.token:
            raise Exception("Not authenticated. Please login first.")

        payload = {"shareId": share_id}
        additional_headers = {"app-login-token": self.token}

        return self._make_request(
            "POST",
            "/api/app/second/share/user/follow",
            payload,
            additional_headers,
        )

    def apply_referral_code(self, code: str) -> Dict[str, Any]:
        """
        Apply a referral/follow code

        Args:
            code: Referral code to apply

        Returns:
            API response as dictionary

        Raises:
            Exception: If not authenticated or request fails
        """
        if not self.token:
            raise Exception("Not authenticated. Please login first.")

        payload = {"code": code}
        additional_headers = {"app-login-token": self.token}

        return self._make_request(
            "POST",
            "/api/app/second/share/user/follow/code",
            payload,
            additional_headers,
        )
    def logout(self) -> Dict[str, Any]:
        """
        Logout current user session

        Returns:
            API response as dictionary

        Raises:
            Exception: If not authenticated or request fails
        """
        if not self.token:
            raise Exception("Not authenticated. Please login first.")

        payload = {"typeId": 22}
        additional_headers = {"app-login-token": self.token}

        return self._make_request(
            "POST",
            "/api/app/basis/article",
            payload,
            additional_headers,
        )


@dataclass
class AccountCredentials:
    """Data class for account credentials"""

    email: str
    password: str
    is_validator: bool = True


def read_credentials_from_csv(csv_path: str) -> List[AccountCredentials]:
    """
    Read account credentials from CSV file

    CSV format should be:
    email,password,is_validator (optional)
    user1@example.com,pass123,true
    user2@example.com,pass456,false

    Args:
        csv_path: Path to CSV file containing credentials

    Returns:
        List of AccountCredentials objects

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    credentials = []

    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader( line for line in file if line.strip() and not line.lstrip().startswith("#"))
        # Validate headers
        required_fields = {"email", "password"}
        if not required_fields.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"CSV must contain at least these columns: {required_fields}. "
                f"Found: {reader.fieldnames}"
            )

        for row_num, row in enumerate(
            reader, start=2
        ):  # start=2 because row 1 is header
            email = row.get("email", "").strip()
            password = row.get("password", "").strip()

            if not email:
                print(f"Warning: Skipping row {row_num} - missing email")
                continue

            # Parse is_validator field (default to True if not specified)
            is_validator_str = row.get("is_validator", "true").strip().lower()
            is_validator = is_validator_str in ("true", "1", "yes", "y")

            credentials.append(
                AccountCredentials(
                    email=email, password=password, is_validator=is_validator
                )
            )

    return credentials


def process_multiple_accounts(
    csv_path: str, referral_code: str, is_show_all_followed: str, config: Optional[APIConfig] = None
) -> List[Dict[str, Any]]:
    """
    Process multiple accounts from CSV file

    Args:
        csv_path: Path to CSV file with credentials
        referral_code: Referral code to apply to all accounts
        config: Optional APIConfig object

    Returns:
        List of results for each account
    """
    credentials_list = read_credentials_from_csv(csv_path)
    results = []

    print(f"Found {len(credentials_list)} accounts to process\n")

    for idx, creds in enumerate(credentials_list, start=1):
        result = {
            "account_number": idx,
            "email": creds.email,
            "login_success": False,
            "referral_success": False,
            "logout_success": False,   # 👈 NEW
            "token": None,
            "referral_response": None,
            "logout_response": None,   # 👈 NEW
            "error": None,
        }

        try:
            print(f"[{idx}/{len(credentials_list)}] Processing: {creds.email}")

            # Create new client for each account
            client = BGolAPIClient(config)

            # Login
            print(f"  ├─ Logging in...")
            token = client.login(
                email=creds.email,
                password=creds.password,
                is_validator=creds.is_validator,
            )
            result["login_success"] = True
            result["token"] = token
            print(f"  ├─ Login successful! Token: {token[:20]}...")

            if is_show_all_followed:
                share_id = client.get_show_all_followed()
                print(f"  ├─ Following share ID: {share_id}")
                if share_id:
                    follow_response = client.follow_share(share_id)
                    print(f"  └─ Follow response: {follow_response}")
                else:
                    print(f"  └─ No share ID found to follow.")
            else:
                print(f"  ├─ No share ID provided, skipping follow step.")
                # Apply referral code
                print(f"  ├─ Applying referral code: {referral_code}")
                referral_response = client.apply_referral_code(referral_code)
                result["referral_success"] = True
                result["referral_response"] = referral_response
                if referral_response.get('resultCode') is True:
                    print(f"  └─ Referral applied successfully! Response: {referral_response}")
                else:
                    print(f"  └─ Referral application failed. Response: {referral_response}")
                # Logout
                # print(f"  ├─ Logging out...")
                # logout_response = client.logout()
                # result["logout_success"] = True
                # result["logout_response"] = logout_response
                # print(f"  └─ Logout successful!")

        except Exception as e:
            result["error"] = str(e)
            print(f"  └─ Error: {e}")

        results.append(result)
        # ⏳ Delay 1 second before next account
        sleep_time = random.uniform(6, 12)
        print(f"Sleeping {sleep_time:.1f}s...")
        time.sleep(sleep_time)
    return results


def save_results_to_file(
    results: List[Dict[str, Any]], output_path: str = "results.json"
):
    """
    Save processing results to JSON file

    Args:
        results: List of result dictionaries
        output_path: Path to output file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {output_path}")


def print_summary(results: List[Dict[str, Any]]):
    """
    Print summary of processing results

    Args:
        results: List of result dictionaries
    """
    total = len(results)
    login_success = sum(1 for r in results if r["login_success"])
    referral_success = sum(1 for r in results if r["referral_success"])
    errors = sum(1 for r in results if r["error"])

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total accounts processed: {total}")
    print(f"Successful logins: {login_success}/{total}")
    print(f"Successful referral applications: {referral_success}/{total}")
    print(f"Errors: {errors}/{total}")
    print("=" * 60)



def main():
    """Main execution function"""
    # Get CSV path and referral code from command line args or environment
    csv_path = os.getenv("CSV_PATH", "credentials.csv")

    # Check if CSV file exists
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found at: {csv_path}")
        print("\nPlease create a CSV file with the following format:")
        print("email,password,is_validator")
        print("user1@example.com,pass123,true")
        print("user2@example.com,pass456,false")
        return 1

    try:
        
        # Process all accounts from CSV
        referral_code = os.getenv("REFERRAL_CODE")
        is_show_all_followed = os.getenv("IS_SHOW_ALL_FOLLOWED", "false").lower() == "true"
        if not referral_code:
            print("Error: REFERRAL_CODE not set in .env")
            return 1
        results = process_multiple_accounts(csv_path, referral_code=referral_code, is_show_all_followed=is_show_all_followed)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f"results_{timestamp}.json"

        save_results_to_file(results, output_file)
        # Print summary
        print_summary(results)
        return 0

    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
