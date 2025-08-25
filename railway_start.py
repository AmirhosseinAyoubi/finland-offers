
import os
import sys
import asyncio
from fin_deals_bot import loop_forever


def main_railway():
    print("Starting Finnish Deals Bot on Railway...")

    required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing = [k for k in required_vars if not os.getenv(k)]
    if missing:
        print(f"Missing environment variables: {missing}")
        print("Set them in Railway → Variables tab.")
        return 1

    stores_path = os.getenv("STORES_PATH", "stores.yaml")
    hours = float(os.getenv("RUN_EVERY_HOURS", "12"))

    print(f"Env OK. Running loop every {hours}h using {stores_path}...")

    try:
        asyncio.run(loop_forever(stores_path, every_hours=hours))
        return 0
    except KeyboardInterrupt:
        print("Stopped by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main_railway())
