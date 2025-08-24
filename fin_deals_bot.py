import os
import re
import sys
import time
import json
import math
import html
import asyncio
import sqlite3
import logging
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from dotenv import load_dotenv
import yaml

try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: Translation not available. Install deep-translator for translation support.")

playwright = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fin-deals-bot")


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR").strip()
MIN_HOURS_BETWEEN_REPOSTS = float(os.getenv("MIN_HOURS_BETWEEN_REPOSTS", "72"))
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"

DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "seen.sqlite")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,fi;q=0.8",
}


translator = None

def init_translator():
    """Initialize the translator."""
    global translator
    if TRANSLATION_AVAILABLE and translator is None:
        try:
            translator = GoogleTranslator(source='fi', target='en')
            log.info("Translation service initialized")
        except Exception as e:
            log.warning("Failed to initialize translator: %s", e)
            return False
    return translator is not None

def translate_text(text: str, source_lang: str = 'fi', target_lang: str = 'en') -> str:
    """Translate text from Finnish to English."""
    if not translator or not text or len(text.strip()) < 3:
        return text
    
    try:
        clean_text = text.strip()
        if len(clean_text) < 3:
            return text
        
        translated = translator.translate(clean_text)
        
        if not translated or translated == clean_text:
            return text
            
        return translated
    except Exception as e:
        log.debug("Translation failed for '%s': %s", text[:50], e)
        return text

def translate_product_info(title: str, store: str) -> tuple[str, str]:
    if not ENABLE_TRANSLATION:
        return title, ""
    
    if not init_translator():
        return title, ""
    
    translated_title = translate_text(title)
    
    if translated_title != title and translated_title:
        return translated_title, title
    else:
        return title, ""

class Product(BaseModel):
    store: str
    title: str
    url: str
    price_current: float
    price_original: float
    currency: str = DEFAULT_CURRENCY
    image: Optional[str] = None

    @property
    def discount_pct(self) -> float:
        if self.price_original <= 0:
            return 0.0
        return max(0.0, (1.0 - (self.price_current / self.price_original)) * 100.0)

# ------------------------------
# DB
# ------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            price_current REAL NOT NULL,
            posted_at_utc TEXT NOT NULL
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_posted_url ON posted(url)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_posted_url_price ON posted(url, price_current)")
    conn.commit()
    conn.close()

def was_recently_posted(url: str, price_current: float, min_hours: float) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT posted_at_utc FROM posted WHERE url=? AND ABS(price_current-?) < 0.01 "
        "ORDER BY posted_at_utc DESC LIMIT 1",
        (url, price_current),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    ts = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts) < timedelta(hours=min_hours)

def mark_posted(url: str, price_current: float):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO posted (url, price_current, posted_at_utc) VALUES (?, ?, ?)",
        (url, price_current, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

_price_regex = re.compile(r"(\d+[.,]?\d*)")
def parse_price(text: str) -> Optional[float]:

    if not text:
        return None
    t = text.replace("\xa0", " ").strip()
    t = re.sub(r"[^0-9,.\s]", "", t)
    t = t.replace(" ", "")
    if "," in t and "." in t:
        t = t.replace(".", "")
        t = t.replace(",", ".")
    else:
        if "," in t and t.count(",") == 1 and t.count(".") == 0:
            t = t.replace(",", ".")
    try:
        return float(t)
    except:
        m = _price_regex.findall(text)
        if not m:
            return None
        val = m[-1].replace(",", ".")
        try:
            return float(val)
        except:
            return None

def absolutize_url(base: str, href: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base, href)

def extract_ld_json_prices(soup: BeautifulSoup) -> List[Dict[str, Any]]:

    results = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, list):
            items = data
        else:
            items = [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            typ = item.get("@type") or item.get("@graph", [{}])[0].get("@type")
            if (typ == "Product") or ("name" in item and ("offers" in item or "offers" in item.get("@graph", {}))):
                name = item.get("name") or ""
                url = item.get("url") or ""
                image = None
                if isinstance(item.get("image"), list):
                    image = item.get("image")[0]
                elif isinstance(item.get("image"), str):
                    image = item.get("image")
                offers = item.get("offers")
                price = None
                currency = DEFAULT_CURRENCY
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("lowPrice")
                    currency = offers.get("priceCurrency") or currency
                elif isinstance(offers, list) and offers:
                    price = offers[0].get("price") or offers[0].get("lowPrice")
                    currency = offers[0].get("priceCurrency") or currency

                price_original = None
                for key in ["priceOriginal", "priceBeforeDiscount", "msrp", "listPrice", "priceWas"]:
                    if key in item:
                        price_original = item.get(key)
                        break

                results.append({
                    "name": name,
                    "url": url,
                    "image": image,
                    "price": float(price) if price is not None else None,
                    "priceOriginal": float(price_original) if price_original is not None else None,
                    "currency": currency
                })
    return results


async def fetch_static(url: str) -> str:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

async def fetch_with_pagination(url: str, max_pages: int = 3) -> str:
    all_content = []
    
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    page_url = url
                else:
                    if 'tokmanni.fi' in url:
                        page_url = f"{url}?p={page}"
                    elif 'prisma.fi' in url:
                        page_url = f"{url}?page={page}"
                    else:
                        page_url = f"{url}?p={page}"
                
                log.debug(f"Fetching page {page}: {page_url}")
                r = await client.get(page_url)
                r.raise_for_status()
                
                content = r.text
                all_content.append(content)
                
                soup = BeautifulSoup(content, 'html.parser')
                if 'tokmanni.fi' in url:
                    products = soup.find_all('li', class_='item product product-item')
                else:
                    products = soup.find_all('li', attrs={'data-test-id': lambda x: x and 'products-list-item' in x})
                
                if len(products) == 0:
                    log.debug(f"No products found on page {page}, stopping pagination")
                    break
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                log.debug(f"Failed to fetch page {page}: {e}")
                break
    
    return "\n".join(all_content)

async def fetch_dynamic(url: str, wait_ms: int = 1500) -> str:
    global playwright
    try:
        if playwright is None:
            from playwright.async_api import async_playwright
            playwright = async_playwright
        async with playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(wait_ms)
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        log.warning(f"Playwright failed for {url}: {e}. Falling back to static scraping.")
        return await fetch_static(url)


class StoreConfig(BaseModel):
    name: str
    url: str
    dynamic: bool = False
    item_selector: str
    link_selector: str
    price_current_selector: str
    price_original_selector: Optional[str] = None

def load_stores(path: str) -> List[StoreConfig]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    stores = [StoreConfig(**s) for s in data.get("stores", [])]
    return stores

def parse_products_from_html(store: StoreConfig, html_text: str) -> List[Product]:
    soup = BeautifulSoup(html_text, "lxml")

    products: List[Product] = []
    ld_items = extract_ld_json_prices(soup)
    for it in ld_items:
        if it.get("price") is None:
            continue
        price_current = float(it["price"])
        price_original = it.get("priceOriginal")
        if price_original is None:
            continue
        url = it.get("url") or ""
        if not url:
            can = soup.find("link", {"rel": "canonical"})
            if can and can.get("href"):
                url = can.get("href")
        products.append(Product(
            store=store.name,
            title=it.get("name") or "Untitled",
            url=url,
            price_current=price_current,
            price_original=float(price_original),
            currency=it.get("currency") or DEFAULT_CURRENCY,
            image=it.get("image"),
        ))

    if not products:
        for card in soup.select(store.item_selector):
            a = card.select_one(store.link_selector)
            if not a or not a.get("href"):
                continue
            url = absolutize_url(store.url, a.get("href"))

            title = a.get("title") or a.get("aria-label") or a.get_text(strip=True) or "Untitled"

            current_el = card.select_one(store.price_current_selector)
            original_el = None
            if store.price_original_selector:
                original_el = card.select_one(store.price_original_selector)

            price_current = parse_price(current_el.get_text(" ", strip=True) if current_el else "")
            price_original = parse_price(original_el.get_text(" ", strip=True) if original_el else "") if original_el else None

            if price_original is None and current_el:
                text_block = current_el.get_text(" ", strip=True)
                nums = re.findall(r"\d+[.,]?\d*", text_block)
                if len(nums) >= 2:
                    price_current = parse_price(nums[-1])
                    price_original = parse_price(nums[0])

            if price_current is None or price_original is None:
                continue

            products.append(Product(
                store=store.name,
                title=title,
                url=url,
                price_current=price_current,
                price_original=price_original,
                currency=DEFAULT_CURRENCY,
            ))

    return products


async def telegram_send_message(token: str, chat_id: str, text: str, disable_preview: bool = False):
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_preview,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(api_url, data=payload)
        if r.status_code != 200:
            log.error("Telegram send failed: %s", r.text)
        r.raise_for_status()

def format_product_msg(p: Product) -> str:
    url = html.escape(p.url)
    pct = f"{p.discount_pct:.0f}%"
    cur = html.escape(p.currency or DEFAULT_CURRENCY)
    price_c = f"{p.price_current:.2f} {cur}"
    price_o = f"{p.price_original:.2f} {cur}"
    store = html.escape(p.store)
    
    translated_title, original_title = translate_product_info(p.title, p.store)
    
    lines = [
        f"🧭 <b>{store}</b>",
        f"🔖 <a href=\"{url}\">{html.escape(translated_title)}</a>",
        f"💸 {price_c}  <s>{price_o}</s>",
        f"📉 Discount: <b>{pct}</b>",
    ]
    
    if original_title and original_title != translated_title:
        lines.append(f"🇫🇮 <i>{html.escape(original_title)}</i>")
    
    return "\n".join(lines)

async def run_once(stores_path: str, min_discount_pct: float = 10.0, max_items_per_store: int = 30):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.")
        sys.exit(1)

    init_db()
    stores = load_stores(stores_path)
    if not stores:
        log.warning("No stores configured in %s", stores_path)
        return

    total_found = 0
    for store in stores:
        log.info("Scanning %s – %s", store.name, store.url)
        try:
            if 'tokmanni.fi' in store.url:
                html_text = await fetch_with_pagination(store.url, max_pages=3)
            else:
                html_text = await (fetch_dynamic(store.url) if store.dynamic else fetch_static(store.url))
        except Exception as e:
            log.error("Fetch failed for %s: %s", store.url, e)
            continue

        products = parse_products_from_html(store, html_text)
        log.info("Parsed %d products from %s", len(products), store.name)

        deals = [p for p in products if p.discount_pct >= min_discount_pct and p.price_current > 0 and p.price_original > 0]
        deals.sort(key=lambda p: p.discount_pct, reverse=True)

        count = 0
        for p in deals:
            if was_recently_posted(p.url, p.price_current, MIN_HOURS_BETWEEN_REPOSTS):
                continue
            msg = format_product_msg(p)
            try:
                await telegram_send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg, disable_preview=False)
                mark_posted(p.url, p.price_current)
                total_found += 1
                count += 1
                await asyncio.sleep(0.7)
            except Exception as e:
                log.error("Telegram failed for %s: %s", p.url, e)
            if count >= max_items_per_store:
                break

    log.info("Done. Announced %d deals (>= %.0f%%).", total_found, min_discount_pct)

async def loop_forever(stores_path: str, every_hours: float = 12.0):
    while True:
        start = time.monotonic()
        try:
            await run_once(stores_path)
        except Exception as e:
            log.exception("Run failed: %s", e)
        elapsed = (time.monotonic() - start) / 3600.0
        wait_hours = max(0.0, every_hours - elapsed)
        wait_seconds = int(wait_hours * 3600)
        log.info("Sleeping ~%d seconds (%.1f hours) before next run.", wait_seconds, wait_hours)
        await asyncio.sleep(wait_seconds or 1)

def main():
    parser = argparse.ArgumentParser(description="Find >10% discounts on Finnish stores and post to Telegram.")
    parser.add_argument("--stores", default="stores.yaml", help="Path to YAML stores config")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    parser.add_argument("--loop", action="store_true", help="Run forever every ~12h")
    parser.add_argument("--hours", type=float, default=12.0, help="Interval hours for --loop")
    args = parser.parse_args()

    if not os.path.exists(args.stores):
        log.error("Stores config not found at %s", args.stores)
        sys.exit(1)

    if args.run_once:
        asyncio.run(run_once(args.stores))
    elif args.loop:
        asyncio.run(loop_forever(args.stores, every_hours=args.hours))
    else:
        asyncio.run(run_once(args.stores))

if __name__ == "__main__":
    main()
