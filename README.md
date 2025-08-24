# Fin Deals Bot (Finland, >50% discounts ➜ Telegram)

This is a **plug-and-play Python bot** that checks Finnish online stores' sale pages, finds products discounted **50% or more**, and posts them to a **Telegram channel**. It runs once or on a **24h schedule**.

> ⚠️ **Respect each site's Terms of Service and robots.txt.** Use reasonable rates, and be prepared to update selectors when sites change layout.

---

## Quick start

### Option 1: Automated Setup (Recommended)
Run the setup script which will guide you through the process:

```bash
python setup.py
```

### Option 2: Windows Users
Double-click `start.bat` or run `start.ps1` in PowerShell for an interactive setup.

### Option 3: Manual Setup
1) **Create a Telegram bot** with [@BotFather] and get the bot token.  
2) Create or choose a **Telegram channel**. Add your bot to the channel as **Admin** (so it can post).  
3) Get your channel's `chat_id` (use a handle like `@yourchannelhandle` or the numeric id).  
4) Copy `.env.example` to `.env` and fill in the values.  
5) Add or adjust the stores you want to scan in `stores.yaml`.  
6) Install and run:

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fin_deals_bot.py --run-once
```

To run **daily** (every 24h), either:
```bash
python fin_deals_bot.py --loop
```
or use cron/systemd/docker (see below).

---

## Files
- `fin_deals_bot.py` – main script (scraper, filtering, Telegram poster, scheduler).
- `stores.yaml` – list of sale pages + CSS selectors per store (edit this).
- `setup.py` – automated setup script for easy configuration.
- `start.bat` / `start.ps1` – Windows quick start scripts.
- `requirements.txt` – dependencies.
- `.env.example` – environment variables template.
- `Dockerfile` – containerized run (cron-friendly).
- `README.md` – this file.

---

## Configure stores

Open `stores.yaml` and put sale pages you care about. For each store you specify:
- `name`: Label for the store.
- `url`: A **sale/clearance** page (category or search with discounts).
- `item_selector`: CSS selector for each product card.
- `link_selector`: CSS selector inside each card for the product `<a href>`.
- `price_current_selector`: CSS selector for current (discounted) price text.
- `price_original_selector`: CSS selector for original price text (or leave empty if site prints it differently).
- `dynamic`: `true` if page needs JS rendering (we'll use Playwright), otherwise `false` for static fetch.

> The repo ships with **10+ popular Finnish stores** including Prisma, Tokmanni, Verkkokauppa, Gigantti, Power, K-Citymarket, S-kaupat, Lidl, H&M, and Zara. You can add more stores or modify existing ones by inspecting the target pages (right-click → Inspect).

If a site exposes JSON‑LD (`<script type="application/ld+json">`) containing price and original price, the bot will try to auto-read those too.

---

## Deduping & DB

We use a small `sqlite` DB (`data/seen.sqlite`) so we don't repost the same product+price again. If you *want* to re-announce, bump the `min_hours_between_reposts` in the script or delete the DB file.

---

## Telegram setup tips

- Add your bot to your channel **as Admin** (important!).
- For `TELEGRAM_CHAT_ID`, you can:
  - Use your **channel handle** like `@deals_oulu` (easy), or
  - Use the numeric id (e.g., `-1001234567890`). One way to get it is to send a message in the channel and call `getUpdates` for your bot, or use helper bots like `@getidsbot`.
- Make sure **privacy mode** doesn't block channel posts.

---

## Cron example

Edit your user crontab with `crontab -e` and add:

```
0 9 * * * cd /path/to/fin-deals-bot && /path/to/.venv/bin/python fin_deals_bot.py --run-once >> cron.log 2>&1
```

This runs daily at **09:00** local time. Adjust as needed.

---

## Docker

Build and run:

```bash
docker build -t fin-deals-bot .
docker run --env-file .env -v "$(pwd)/data:/app/data" fin-deals-bot --run-once
```

To loop forever (every ~24h):

```bash
docker run --env-file .env -v "$(pwd)/data:/app/data" fin-deals-bot --loop
```

---

## Legal & ethical notes

- **Always** check site Terms of Service and **robots.txt** before scraping.
- Use a **polite rate** and cache where possible.
- Stop scraping if a site forbids it or asks you to stop.
- Prefer official APIs, feeds, or affiliate endpoints if offered.

---

## Extending

To add a store, copy an entry in `stores.yaml`, paste selectors for product card, current price, original price, and link. If the page is JS-heavy, set `dynamic: true` so Playwright is used to render before parsing.

Happy hunting! 🇫🇮
