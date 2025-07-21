import os
import re
import requests
import urllib.parse
from time import sleep
from playwright.sync_api import sync_playwright

# Extract pin ID from full URL
def extract_pin_id_from_url(pin_url):
    match = re.search(r'/pin/(\d{10,20})', pin_url)
    return match.group(1) if match else None

# Try 'originals' first, fallback to 1200x
def get_highest_quality_url(image_url, session):
    original_url = image_url.replace("/600x/", "/originals/")
    response = session.head(original_url)
    return original_url if response.status_code == 200 else image_url.replace("/600x/", "/1200x/")

# Extract og:image from the pin page
def extract_image_url(playwright, url):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, timeout=30000)
        page.wait_for_selector("meta[property='og:image']", state="attached", timeout=15000)
        image_url = page.locator("meta[property='og:image']").get_attribute("content")
    except:
        image_url = None
    finally:
        browser.close()
    return image_url

# Download image using session
def download_image(pin_url, session, playwright):
    pin_id = extract_pin_id_from_url(pin_url)
    if not pin_id:
        print(f"❌ Skipped invalid URL: {pin_url}")
        return

    print(f"🔎 Processing pin: {pin_id}")
    image_url = extract_image_url(playwright, pin_url)
    if not image_url:
        print(f"❌ Could not extract image for pin {pin_id}")
        return

    final_url = get_highest_quality_url(image_url, session)
    try:
        img_data = session.get(final_url).content
        os.makedirs("Pintrest_data", exist_ok=True)
        file_path = os.path.join("Pintrest_data", f"{pin_id}.jpg")
        with open(file_path, "wb") as f:
            f.write(img_data)
        print(f"✅ Saved: {file_path}")
    except Exception as e:
        print(f"❌ Download failed for pin {pin_id}: {e}")

# Scrape pin URLs from Pinterest keyword search
def get_pin_urls_by_keyword(keyword, count, playwright):
    search_term = urllib.parse.quote_plus(keyword)
    search_url = f"https://www.pinterest.com/search/pins/?q={search_term}"

    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"🔍 Searching for: {keyword}")
    page.goto(search_url, timeout=30000)
    sleep(5)  # allow JS content to render

    # Scroll to load more pins
    while len(page.locator("a[href^='/pin/']").all()) < count:
        page.mouse.wheel(0, 3000)
        sleep(2)

    # Extract unique pin URLs
    anchors = page.locator("a[href^='/pin/']").all()
    pin_urls = []
    seen_ids = set()
    for a in anchors:
        href = a.get_attribute("href")
        if href:
            full_url = urllib.parse.urljoin("https://www.pinterest.com", href)
            pin_id = extract_pin_id_from_url(full_url)
            if pin_id and pin_id not in seen_ids:
                seen_ids.add(pin_id)
                pin_urls.append(full_url)
        if len(pin_urls) >= count:
            break

    browser.close()
    print(f"🔗 Found {len(pin_urls)} pins.")
    return pin_urls

# Main batch processing
def keyword_based_download(keyword, count):
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25)
    session.mount("https://", adapter)

    with sync_playwright() as playwright:
        pin_urls = get_pin_urls_by_keyword(keyword, count, playwright)
        for url in pin_urls:
            download_image(url, session, playwright)

# === Entry Point ===
if __name__ == "__main__":
    keyword = input("Enter search keyword: ").strip()
    count = int(input("How many images to download? ").strip())
    keyword_based_download(keyword, count)
