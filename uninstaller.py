import os
import sys
import time
import winreg
import subprocess

APP_NAME = "Windows11Alert"
EXE_NAME = "Windows11Alert.exe"


def remove_from_startup():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)

        print("Removed from startup successfully.")

    except FileNotFoundError:
        print("App was not found in startup.")

    except Exception as e:
        print("Failed to remove from startup:", e)


def kill_running_app():
    try:
        current_pid = os.getpid()

        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}"],
            capture_output=True,
            text=True,
            shell=False
        )

        if EXE_NAME.lower() not in result.stdout.lower():
            print(f"{EXE_NAME} is not running.")
            return

        print(f"{EXE_NAME} is running. Trying to close it...")

        # Force close the running app
        subprocess.run(
            ["taskkill", "/F", "/IM", EXE_NAME],
            capture_output=True,
            text=True,
            shell=False
        )

        time.sleep(1)

        # Check again
        check = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}"],
            capture_output=True,
            text=True,
            shell=False
        )

        if EXE_NAME.lower() in check.stdout.lower():
            print(f"Failed to close {EXE_NAME}.")
        else:
            print(f"{EXE_NAME} closed successfully.")

    except Exception as e:
        print("Failed to close running app:", e)


def main():
    print("Windows11Alert Uninstaller Started")
    print("-" * 40)

    kill_running_app()
    remove_from_startup()

    print("-" * 40)
    print("Uninstall cleanup completed.")


if __name__ == "__main__":
    main()