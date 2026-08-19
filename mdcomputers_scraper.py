#!/usr/bin/env python3
"""
mdcomputers_scraper.py

Scrapes product details from MDComputers.in for a given search term.

Usage:
    python mdcomputers_scraper.py "external harddrive"
    python mdcomputers_scraper.py "external harddrive" --pages 3 --out results.csv

It hits:
    https://mdcomputers.in/?route=product/search&search=<term>

For each product card on the results page(s) it extracts:
    - name
    - price
    - old_price (if the item is discounted)
    - availability (In Stock / Out of Stock, when shown)
    - product_url
    - image_url

Results are printed to the console and saved to a CSV file.

Notes:
    - This targets the current MDComputers OpenCart-based HTML layout
      (product cards with class "product-layout" / "product-thumb").
      If the site changes its markup, the CSS selectors in `parse_page`
      will need to be updated.
    - Be a polite scraper: a short delay is added between page requests,
      and a normal desktop User-Agent header is sent.
"""

import argparse
import csv
import sys
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mdcomputers.in/"
SEARCH_PATH = "?route=product/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(search_term: str, page: int = 1, timeout: int = 20) -> str:
    """Fetch raw HTML for one page of search results."""
    url = (
        f"{BASE_URL}{SEARCH_PATH}"
        f"&search={quote_plus(search_term)}"
        f"&page={page}"
    )
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _clean(text):
    return " ".join(text.split()) if text else None


def parse_page(html: str):
    """Parse one search-results page and return a list of product dicts."""
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # OpenCart-style product cards. MDComputers has used variations of
    # "product-layout product-grid" / "product-thumb transition" over time,
    # so we match loosely on class fragments.
    cards = soup.select("div.product-thumb") or soup.select(".product-layout")

    for card in cards:
        name_tag = card.select_one(".caption h4 a, .caption a, h4 a")
        name = _clean(name_tag.get_text()) if name_tag else None
        product_url = name_tag["href"] if name_tag and name_tag.has_attr("href") else None

        img_tag = card.select_one("img")
        image_url = img_tag.get("src") or img_tag.get("data-src") if img_tag else None

        price_tag = card.select_one(".price-new") or card.select_one(".price")
        price = _clean(price_tag.get_text()) if price_tag else None

        old_price_tag = card.select_one(".price-old")
        old_price = _clean(old_price_tag.get_text()) if old_price_tag else None

        stock_tag = card.select_one(".stock, .availability")
        availability = _clean(stock_tag.get_text()) if stock_tag else None

        if name:  # skip empty/malformed cards
            products.append(
                {
                    "name": name,
                    "price": price,
                    "old_price": old_price,
                    "availability": availability,
                    "product_url": product_url,
                    "image_url": image_url,
                }
            )

    return products


def scrape(search_term: str, pages: int = 1, delay: float = 1.5):
    all_products = []
    for page in range(1, pages + 1):
        print(f"Fetching page {page} for '{search_term}'...", file=sys.stderr)
        try:
            html = fetch_page(search_term, page)
        except requests.RequestException as exc:
            print(f"  Request failed on page {page}: {exc}", file=sys.stderr)
            break

        page_products = parse_page(html)
        if not page_products:
            print(f"  No products found on page {page}, stopping.", file=sys.stderr)
            break

        all_products.extend(page_products)

        if page < pages:
            time.sleep(delay)  # be polite between requests

    return all_products


def save_csv(products, out_path: str):
    if not products:
        print("No products to save.", file=sys.stderr)
        return
    fieldnames = ["name", "price", "old_price", "availability", "product_url", "image_url"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    print(f"Saved {len(products)} products to {out_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Scrape product details from MDComputers.in")
    parser.add_argument("search_term", help='Search term, e.g. "external harddrive"')
    parser.add_argument("--pages", type=int, default=1, help="Number of result pages to fetch (default: 1)")
    parser.add_argument("--out", default="mdcomputers_results.csv", help="Output CSV file path")
    args = parser.parse_args()

    products = scrape(args.search_term, pages=args.pages)

    for p in products:
        print(f"{p['name']} | {p['price']} | {p['availability']} | {p['product_url']}")

    save_csv(products, args.out)


if __name__ == "__main__":
    main()
