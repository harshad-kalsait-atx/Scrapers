from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json
import re
import base64
import os

# === Convert link to embed format ===
def convert_scribd_link(url):
    match = re.search(r'https://www\.scribd\.com/[\w\-]+/(\d+)/', url)
    if match:
        return match.group(1), f'https://www.scribd.com/embeds/{match.group(1)}/content'
    else:
        raise ValueError("Invalid Scribd URL")

# === Input and conversion ===
input_url = input("Input Scribd link: ")
doc_id, converted_url = convert_scribd_link(input_url)
print("Embed Link:", converted_url)

# === Setup Chrome options ===
download_path = os.getcwd()  # current directory

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--print-to-pdf-no-header')
prefs = {
    'printing.print_preview_sticky_settings.appState': json.dumps({
        'version': 2,
        'isGcpPromoDismissed': False,
        'selectedDestinationId': 'Save as PDF',
        'recentDestinations': [{
            'id': 'Save as PDF',
            'origin': 'local',
            'account': '',
        }],
        'mediaSize': {
            'name': 'ISO_A4',
            'width_microns': 210000,
            'height_microns': 297000,
            'custom_display_name': 'A4',
        },
        'marginsType': 1,  # no margins
        'scalingType': 3,
        'scaling': '100',
        'isHeaderFooterEnabled': False,
        'isCssBackgroundEnabled': True,
    }),
    'savefile.default_directory': download_path
}
options.add_experimental_option('prefs', prefs)
options.add_argument('--kiosk-printing')  # to skip print dialog

# === Initialize driver ===
driver = webdriver.Chrome(options=options)
driver.get(converted_url)
time.sleep(3)

# === Scroll to load all pages ===
pages = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
for page in pages:
    driver.execute_script("arguments[0].scrollIntoView();", page)
    time.sleep(0.3)
print("✅ Finished Scrolling")

# === Remove unwanted elements ===
driver.execute_script("""
    let top = document.querySelector('.toolbar_top');
    if (top) top.remove();
    let bottom = document.querySelector('.toolbar_bottom');
    if (bottom) bottom.remove();
    let scrollers = document.querySelectorAll('.document_scroller');
    scrollers.forEach(el => el.className = '');
""")
print("✅ Cleaned toolbars and scrollers")

# === Generate PDF using DevTools Protocol ===
print("📄 Saving as PDF...")

pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
    "printBackground": True,
    "landscape": False,
    "paperWidth": 8.27,    # A4 width in inches
    "paperHeight": 11.69,  # A4 height in inches
    "marginTop": 0,
    "marginBottom": 0,
    "marginLeft": 0,
    "marginRight": 0,
    "preferCSSPageSize": True,
})
pdf_bytes = base64.b64decode(pdf_data['data'])

# Save PDF to disk
output_filename = f"{doc_id}.pdf"
with open(output_filename, "wb") as f:
    f.write(pdf_bytes)

print(f"✅ PDF saved as: {output_filename}")
driver.quit()
