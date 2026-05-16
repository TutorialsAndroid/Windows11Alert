import os
import sys
import socket
import platform
import requests
import psutil
import winreg
import traceback
import subprocess
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ==============================
# APP CONFIG
# ==============================

APP_NAME = "Windows11Alert"
LOG_FILE = r"C:\ProgramData\Windows11Alert_log.txt"
LAST_SENT_FILE = r"C:\ProgramData\Windows11Alert_last_event.txt"

# ==============================
# BASE DIR + ENV
# ==============================

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ==============================
# LOGGING
# ==============================

def write_log(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            f.flush()
    except Exception:
        pass


# ==============================
# AUTO START REGISTRY
# ==============================

def add_to_startup():
    try:
        if getattr(sys, "frozen", False):
            app_path = sys.executable
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)

        write_log(f"Added to startup: {app_path}")

    except Exception:
        write_log("Failed to add to startup")
        write_log(traceback.format_exc())


# ==============================
# PC DETAILS
# ==============================

def get_username():
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME", "Unknown User")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "Unable to get local IP"


def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org", timeout=5)
        return response.text.strip()
    except Exception:
        return "Unable to get public IP"


def get_ram_info():
    try:
        ram = psutil.virtual_memory()
        total_gb = ram.total / (1024 ** 3)
        available_gb = ram.available / (1024 ** 3)
        return f"{total_gb:.2f} GB Total, {available_gb:.2f} GB Available"
    except Exception:
        return "Unable to get RAM info"


def get_boot_time():
    try:
        boot_timestamp = psutil.boot_time()
        boot_time = datetime.fromtimestamp(boot_timestamp)
        return boot_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Unable to get boot time"


# ==============================
# TELEGRAM
# ==============================

def send_telegram_message(message, timeout_seconds=10):
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            write_log("Telegram token/chat id missing. Check .env file.")
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, data=data, timeout=timeout_seconds)

        write_log(f"Telegram status: {response.status_code}")
        write_log(f"Telegram response: {response.text}")

        return response.status_code == 200

    except Exception:
        write_log("Telegram send error")
        write_log(traceback.format_exc())
        return False


# ==============================
# WINDOWS EVENT LOG READER
# ==============================

def get_last_sent_event_id():
    try:
        if os.path.exists(LAST_SENT_FILE):
            with open(LAST_SENT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass

    return ""


def save_last_sent_event_id(event_key):
    try:
        with open(LAST_SENT_FILE, "w", encoding="utf-8") as f:
            f.write(event_key)
    except Exception:
        write_log("Failed to save last sent event id")
        write_log(traceback.format_exc())


def run_powershell(command):
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command
            ],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="ignore"
        )

        if result.returncode != 0:
            write_log("PowerShell error:")
            write_log(result.stderr)

        return result.stdout.strip()

    except Exception:
        write_log("PowerShell run failed")
        write_log(traceback.format_exc())
        return ""


def get_previous_shutdown_event():
    """
    Reads recent Windows System events:
    1074 = planned shutdown/restart initiated by user/app
    6006 = Event Log service stopped, usually clean shutdown
    6008 = unexpected shutdown
    """

    ps_command = r"""
$events = Get-WinEvent -FilterHashtable @{
    LogName='System'
    Id=1074,6006,6008
} -MaxEvents 10 | Select-Object TimeCreated, Id, ProviderName, Message

$events | ConvertTo-Json -Depth 4
"""

    output = run_powershell(ps_command)

    if not output:
        write_log("No PowerShell event output")
        return None

    try:
        import json
        events = json.loads(output)

        if isinstance(events, dict):
            events = [events]

        if not events:
            write_log("No shutdown events found")
            return None

        # Pick first event that happened before current boot time.
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        for event in events:
            event_time_raw = event.get("TimeCreated", "")
            event_id = event.get("Id", "")
            provider = event.get("ProviderName", "")
            message = event.get("Message", "")

            event_time = parse_powershell_date(event_time_raw)

            if event_time and event_time < boot_time:
                event_key = f"{event_id}_{event_time.strftime('%Y-%m-%d_%H-%M-%S')}"

                return {
                    "event_key": event_key,
                    "event_id": event_id,
                    "provider": provider,
                    "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": clean_event_message(message)
                }

        write_log("No event before current boot found")
        return None

    except Exception:
        write_log("Failed to parse event log JSON")
        write_log(output)
        write_log(traceback.format_exc())
        return None


def parse_powershell_date(value):
    try:
        # PowerShell JSON date can come like: /Date(1778910000000)/
        match = re.search(r"\d+", str(value))
        if match:
            timestamp_ms = int(match.group(0))
            return datetime.fromtimestamp(timestamp_ms / 1000)

        # Fallback ISO parsing
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

    except Exception:
        return None


def clean_event_message(message):
    if not message:
        return "No message available"

    message = str(message)
    message = message.replace("\r", " ").replace("\n", " ")
    message = re.sub(r"\s+", " ", message).strip()

    if len(message) > 900:
        message = message[:900] + "..."

    return message


# ==============================
# MESSAGE BUILDERS
# ==============================

def build_previous_shutdown_message(event):
    pc_name = socket.gethostname()
    username = get_username()
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    boot_time = get_boot_time()

    event_id = event.get("event_id", "Unknown")
    event_time = event.get("event_time", "Unknown")
    provider = event.get("provider", "Unknown")
    event_message = event.get("message", "Unknown")

    if str(event_id) == "1074":
        event_type = "Planned Shutdown / Restart"
    elif str(event_id) == "6006":
        event_type = "Clean Shutdown"
    elif str(event_id) == "6008":
        event_type = "Unexpected Shutdown"
    else:
        event_type = "Shutdown / Restart Event"

    return f"""
🔴 <b>Previous PC Shutdown/Restart Detected</b>

🖥️ <b>PC Name:</b> {pc_name}
👤 <b>User:</b> {username}

🌐 <b>Local IP:</b> {local_ip}
🌍 <b>Public IP:</b> {public_ip}

📅 <b>Shutdown Event Time:</b> {event_time}
📅 <b>Report Sent At:</b> {current_time}
⏱️ <b>Current Boot Time:</b> {boot_time}

⚡ <b>Event Type:</b> {event_type}
🧾 <b>Event ID:</b> {event_id}
🏷️ <b>Provider:</b> {provider}

📝 <b>Windows Message:</b>
{event_message}
"""


def build_startup_message():
    pc_name = socket.gethostname()
    username = get_username()
    local_ip = get_local_ip()
    public_ip = get_public_ip()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    os_name = platform.system()
    os_version = platform.version()
    os_release = platform.release()
    processor = platform.processor()
    architecture = platform.machine()
    ram_info = get_ram_info()
    boot_time = get_boot_time()

    return f"""
🟢 <b>PC Turned On</b>

🖥️ <b>PC Name:</b> {pc_name}
👤 <b>User:</b> {username}

🌐 <b>Local IP:</b> {local_ip}
🌍 <b>Public IP:</b> {public_ip}

📅 <b>Date & Time:</b> {current_time}
⏱️ <b>Boot Time:</b> {boot_time}

💻 <b>OS:</b> {os_name} {os_release}
🔢 <b>OS Version:</b> {os_version}
⚙️ <b>Processor:</b> {processor}
🏗️ <b>Architecture:</b> {architecture}
🧠 <b>RAM:</b> {ram_info}
"""


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    try:
        write_log("========================================")
        write_log("Windows11Alert started")
        write_log(f"BASE_DIR: {BASE_DIR}")
        write_log(f"ENV PATH: {env_path}")
        write_log(f"ENV EXISTS: {env_path.exists()}")

        add_to_startup()

        # 1. Previous shutdown/restart report
        last_event = get_previous_shutdown_event()

        if last_event:
            write_log(f"Previous shutdown event found: {last_event}")

            last_sent_event_id = get_last_sent_event_id()

            if last_event["event_key"] != last_sent_event_id:
                previous_message = build_previous_shutdown_message(last_event)
                sent = send_telegram_message(previous_message, timeout_seconds=10)

                if sent:
                    save_last_sent_event_id(last_event["event_key"])
                    write_log("Previous shutdown event sent successfully")
                else:
                    write_log("Previous shutdown event sending failed")
            else:
                write_log("Previous shutdown event already sent earlier")
        else:
            write_log("No previous shutdown event to send")

        # 2. Current startup report
        startup_message = build_startup_message()
        send_telegram_message(startup_message, timeout_seconds=10)

        write_log("Windows11Alert finished")

    except Exception:
        write_log("MAIN ERROR")
        write_log(traceback.format_exc())