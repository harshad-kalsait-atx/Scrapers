import time
import re
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from tqdm import tqdm


def extract_doc_id(scribd_url):
    match = re.search(r'/[\w\-]+/(\d+)', scribd_url)
    return match.group(1) if match else None


def get_embed_url(doc_id):
    return f"https://www.scribd.com/embeds/{doc_id}/content"


def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)


def fetch_clean_pdf(driver, embed_url, scale=0.98):
    driver.get(embed_url)

    # Wait until the document container is loaded
    timeout = time.time() + 30
    while time.time() < timeout:
        try:
            outer = driver.find_element(By.CLASS_NAME, "outer_page_container")
            if outer:
                break
        except:
            time.sleep(0.5)
    else:
        raise TimeoutError("Document did not load in time.")

    # Clean everything except the outer_page_container
    driver.execute_script("""
        const outer = document.querySelector('div.outer_page_container');
        document.body.innerHTML = '';
        document.body.appendChild(outer);
        document.body.style.margin = '0';
    """)

    time.sleep(1)

    # Print to PDF
    result = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27,
        "paperHeight": 11.69,
        "marginTop": 0,
        "marginBottom": 0,
        "marginLeft": 0,
        "marginRight": 0,
        "preferCSSPageSize": True,
        "scale": scale
    })

    return base64.b64decode(result['data'])


def save_pdf(pdf_bytes, output_path):
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f"[+] Saved cleaned PDF: {output_path}")


def scrape_clean_scribd_pdfs(urls):
    for url in tqdm(urls, desc="Downloading Clean Scribd PDFs"):
        driver = setup_driver()
        doc_id = extract_doc_id(url)
        if not doc_id:
            print(f"[-] Invalid Scribd URL: {url}")
            driver.quit()
            continue

        try:
            embed_url = get_embed_url(doc_id)
            print(f"[+] Processing document: {doc_id}")
            pdf_bytes = fetch_clean_pdf(driver, embed_url)
            save_pdf(pdf_bytes, f"{doc_id}.pdf")
        except Exception as e:
            print(f"[!] Failed to process {doc_id}: {e}")
        finally:
            driver.quit()


if __name__ == "__main__":
    scribd_urls = [
        "https://www.scribd.com/document/466329148/requestDocumentResultPage",
        "https://www.scribd.com/presentation/513168371/ABN",
        # Add more links here
    ]
    scrape_clean_scribd_pdfs(scribd_urls)
