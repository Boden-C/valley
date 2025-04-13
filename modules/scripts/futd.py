from datetime import datetime, time as datetime_time
import random
import re
import requests
import schedule
import time
import urllib.parse
import winsound
from typing import Optional, Tuple, Dict

REQUEST_HEADERS = """
"""

PAYLOAD = """
"""

MIN = 10
MAX = 420

START = "08:00"
END = "23:59"


def retry_request(
    url: str,
    headers: Dict[str, str],
    cookies: Dict[str, str],
    data: Dict[str, str],
    max_retries: int = 3,
    retry_delay: int = 5,
) -> Optional[requests.Response]:
    """
    Sends a POST request with retry logic.

    Args:
        url: The URL of the request.
        headers: The headers for the request.
        cookies: The cookies for the request.
        data: The data (request body) for the request.
        max_retries: The maximum number of times to retry the request.
        retry_delay: The delay in seconds between retries.

    Returns:
        The response object if the request is successful, or None if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=data)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Request failed.")
                return None


def extract_message_and_status(html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts the error message and status from the provided HTML.

    Args:
        html: The HTML content containing the message and status.

    Returns:
        A tuple containing the message and status. Returns (None, None) if not found.
    """
    message_pattern = re.compile(
        r"id='win0divDERIVED_REGFRM1_SS_MESSAGE_LONG\$0'><div.*?" r">(.*?)",
        re.DOTALL,
    )

    status_pattern = re.compile(
        r"id='win0divDERIVED_REGFRM1_SSR_STATUS_LONG\$0'><div.*?" r">(.*?)",
        re.DOTALL,
    )

    status_image_pattern = re.compile(
        r'<img src="/cs/DACSPRD/cache/PS_CS_STATUS_(SUCCESS|ERROR)_ICN_1\.gif"',
        re.IGNORECASE,
    )

    message_match = message_pattern.search(html)
    status_match = status_pattern.search(html)

    message: Optional[str] = None
    if message_match:
        inner_html = message_match.group(1)
        message_text_match = re.search(r"<B>Error:\s*</B>(.+)", inner_html, re.DOTALL)
        if message_text_match:
            message = message_text_match.group(1).strip()
    if message is None:  # Fallback if specific div not found or doesn't match inner structure
        message = re.search(r"<B>Error:\s*</B>(.+)", html, re.DOTALL)

    status: Optional[str] = None
    if status_match:
        status_html = status_match.group(1)
        status_image_match = status_image_pattern.search(status_html)
        if status_image_match:
            status = "success" if status_image_match.group(1).upper() == "SUCCESS" else "error"
    if status is None:  # Fallback if specific div not found
        error_image_found = html.find(
            """<img src="/cs/DACSPRD/cache/PS_CS_STATUS_ERROR_ICN_1.gif" width="16" height="16" alt="Error" STYLE="vertical-align:middle;text-align:center;margin-left:12px">"""
        )
        if error_image_found != -1:
            status = "expected"

    return message, status


def run_job():
    global request_url, request_headers, request_cookies, request_data
    response = retry_request(request_url, request_headers, request_cookies, request_data)
    if response:
        message, status = extract_message_and_status(response.text)
        print(f"Message: {message}")
        print(f"Status: {status}")
        if status != "expected":
            print("UNEXPECTED ERROR!!!!")
            winsound.Beep(440, 5000)
            # Optionally clear all scheduled jobs if an unexpected error occurs
            # schedule.clear()
    else:
        print("Request failed after multiple retries.")
        winsound.Beep(200, 5000)
        # Optionally clear all scheduled jobs if the request fails
        # schedule.clear()


def run_job():
    global request_url, request_headers, request_cookies, request_data
    response = retry_request(request_url, request_headers, request_cookies, request_data)
    if response:
        message, status = extract_message_and_status(response.text)
        print(f"Message: {message}")
        print(f"Status: {status}")
        if status != "expected":
            print("UNEXPECTED ERROR!!!!")
            winsound.Beep(440, 5000)
            raise Exception("Unexpected error occurred.")
    else:
        print("Request failed after multiple retries.")
        winsound.Beep(200, 5000)
        raise Exception("Request failed after multiple retries.")


if __name__ == "__main__":
    print("Parsing Headers and Payload...")
    # Split headers into lines and remove leading/trailing whitespace
    header_lines = REQUEST_HEADERS.strip().split("\n")

    # Parse the first line to get the path
    first_line = header_lines[0].strip()
    method, path, _ = first_line.split(" ", 2)

    # Construct the full URL using the base URL inferred from cookies/payload
    base_url = "https://dacs-prd.utshare.utsystem.edu"
    request_url = base_url + path

    # Initialize dictionaries for headers and cookies
    request_headers: Dict[str, str] = {}
    request_cookies: Dict[str, str] = {}

    # Parse header lines
    for line in header_lines[1:]:
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key.lower() == "cookie":
                # Parse cookies into a dictionary
                cookie_list = [cookie.strip() for cookie in value.split(";")]
                for cookie in cookie_list:
                    if "=" in cookie:
                        cookie_key, cookie_value = cookie.split("=", 1)
                        request_cookies[cookie_key.strip()] = cookie_value.strip()
            else:
                request_headers[key] = value

    # Remove headers that requests will handle automatically
    request_headers.pop("Content-Length", None)

    # Parse payload into a dictionary
    payload_dict = urllib.parse.parse_qs(PAYLOAD, keep_blank_values=True)
    # Convert list values to scalars since each key has one value
    request_data: Dict[str, str] = {k: v[0] for k, v in payload_dict.items()}

    print("Running the job once before scheduling...")
    run_job()

    start_time_obj: Optional[datetime_time] = None
    if START is not None:
        try:
            start_time_obj = datetime.strptime(START, "%H:%M").time()
        except ValueError:
            print("Invalid START time format. Starting immediately.")

    end_time_obj: Optional[datetime_time] = None
    if END is not None:
        try:
            end_time_obj = datetime.strptime(END, "%H:%M").time()
        except ValueError:
            print("Invalid END time format. The script will run indefinitely.")

    print("Starting main loop...")
    if START is not None and start_time_obj:
        while True:
            now = datetime.now().time()
            if now >= start_time_obj:
                print(f"Start time ({START}) reached.")
                break
            else:
                wait_seconds = (
                    datetime.combine(datetime.today(), start_time_obj) - datetime.combine(datetime.today(), now)
                ).total_seconds()
                if wait_seconds > 0:
                    wait_time = int(wait_seconds)
                    hours = wait_time // 3600
                    minutes = (wait_time % 3600) // 60
                    seconds = wait_time % 60
                    fancy_wait_time = ""
                    if hours > 0:
                        fancy_wait_time += f"{hours} hr, "
                    if minutes > 0:
                        fancy_wait_time += f"{minutes} min, "
                    fancy_wait_time += f"{seconds} sec"
                    print(f"Waiting for {fancy_wait_time} until {START}...")
                    time.sleep(min(wait_seconds, 60))
                else:
                    print(f"Start time ({START}) has already passed for today. Starting immediately.")
                    break

    while True:
        if end_time_obj:
            now = datetime.now().time()
            if now >= end_time_obj:
                print(f"End time ({END}) reached. Exiting.")
                break

        run_job()

        r = random.randint(MIN, MAX)
        print(f"Sleeping for {r} seconds...")
        time.sleep(r)

    print("Script finished.")
