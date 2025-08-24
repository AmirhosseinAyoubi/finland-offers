
import os
import sys
from fin_deals_bot import main

def main_railway():

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
