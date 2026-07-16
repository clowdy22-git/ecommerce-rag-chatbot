"""
Minimal, polite scraper for demo product data, targeting a scraping-practice
site (safe, no ToS issues). Prices are converted USD->INR for this demo;
for real use, prefer the Kaggle Flipkart dataset (native INR pricing).
"""
import time
import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://webscraper.io/test-sites/e-commerce/allinone"
HEADERS = {"User-Agent": "Mozilla/5.0 (RAG-demo-bot; contact: you@example.com)"}
USD_TO_INR_RATE = 83.0


def _usd_to_inr(price_text: str) -> str:
    match = re.search(r"[\d.]+", price_text or "")
    if not match:
        return price_text or ""
    usd = float(match.group())
    inr = usd * USD_TO_INR_RATE
    return f"\u20b9{inr:,.0f}"


def get_category_links() -> List[str]:
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.select("a[href*='/computers'], a[href*='/phones']"):
        href = a.get("href")
        if href:
            links.add(href if href.startswith("http") else f"https://webscraper.io{href}")
    return list(links)


def scrape_products(max_products: int = 30, delay_sec: float = 0.5) -> List[Dict]:
    products = []
    category_urls = get_category_links() or [BASE_URL]

    for cat_url in category_urls:
        if len(products) >= max_products:
            break
        try:
            resp = requests.get(cat_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".thumbnail")

        for card in cards:
            if len(products) >= max_products:
                break
            title_el = card.select_one(".title")
            price_el = card.select_one(".price")
            desc_el = card.select_one(".description")
            img_el = card.select_one("img")
            if not title_el:
                continue

            img_src = img_el.get("src") if img_el else ""
            if img_src and img_src.startswith("/"):
                img_src = f"https://webscraper.io{img_src}"

            product = {
                "product_id": f"scraped-{len(products) + 1}",
                "title": title_el.get("title") or title_el.text.strip(),
                "category": cat_url.rstrip("/").split("/")[-1],
                "price": _usd_to_inr(price_el.text.strip()) if price_el else None,
                "description": desc_el.text.strip() if desc_el else "",
                "url": cat_url,
                "image_url": img_src or "",
            }
            products.append(product)

        time.sleep(delay_sec)

    return products


if __name__ == "__main__":
    data = scrape_products(max_products=20)
    print(f"Scraped {len(data)} products")
    for p in data[:3]:
        print(p)
