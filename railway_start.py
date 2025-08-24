
import os
import sys
import subprocess
import asyncio
from fin_deals_bot import main

def setup_playwright():
    try:

        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True
        else:
            return True
            
    except Exception as e:
        return True

def main_railway():

    setup_playwright()
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return 1

    try:
        main()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        return 1

if __name__ == "__main__":
    sys.exit(main_railway())
