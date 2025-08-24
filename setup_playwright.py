
import subprocess
import sys
import os

def install_playwright_browsers():
    try:

        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
        else:
            return False
            
    except Exception as e:
        return False

def main():
    if install_playwright_browsers():
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
