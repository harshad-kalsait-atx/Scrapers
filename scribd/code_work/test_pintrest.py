import os
import re
import requests
from playwright.sync_api import sync_playwright

def extract_pin_id_from_url(pin_url):
    match = re.search(r'/pin/(\d{10,20})', pin_url)
    return match.group(1) if match else None

def get_highest_quality_url(image_url):
    original_url = image_url.replace("/600x/", "/1200x/")
    response = requests.head(original_url, headers={"User-Agent": "Mozilla/5.0"})
    return original_url if response.status_code == 200 else image_url.replace("/600x/",  "/originals/")

def download_pinterest_image_with_playwright(pin_url):
    pin_id = extract_pin_id_from_url(pin_url)
    if not pin_id:
        print("❌ Invalid Pinterest URL.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(pin_url, timeout=30000)

        
        # Wait for <meta property="og:image"> to be attached to DOM
        page.wait_for_selector("meta[property='og:image']", state="attached", timeout=15000)
        og_image = page.locator("meta[property='og:image']").get_attribute("content")
        browser.close()

    if not og_image:
        print(f"❌ Could not extract image from pin {pin_id}")
        return

    final_image_url = get_highest_quality_url(og_image)
    headers = {"User-Agent": "Mozilla/5.0"}

    # Download and save image
    os.makedirs("Pintrest_data", exist_ok=True)
    file_path = os.path.join("Pintrest_data", f"{pin_id}.jpg")
    img_data = requests.get(final_image_url, headers=headers).content
    with open(file_path, "wb") as f:
        f.write(img_data)

    print(f"✅ Image saved: {file_path}\n📷 From: {final_image_url}")

# === Run ===
if __name__ == "__main__":
    input_url = input("Enter full Pinterest Pin URL: ").strip()
    download_pinterest_image_with_playwright(input_url)
