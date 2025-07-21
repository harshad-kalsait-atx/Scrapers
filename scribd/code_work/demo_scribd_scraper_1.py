# #Main logic for scraping Scribd documents and saving them as PDFs renamed by document ID.but still issue with pdf handling with multiple pages and multiple documents links.
# # This code logic used in main script.
# import time
# import base64
# import re
# import io
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from PyPDF2 import PdfReader, PdfWriter


# def extract_doc_id(scribd_url):
#     """
#     Extracts document ID from a Scribd URL.
#     """
#     match = re.search(r'/[\w\-]+/(\d+)', scribd_url)
#     if match:
#         return match.group(1)
#     else:
#         print(f"[!] Could not find document ID from URL: {scribd_url}")
#         return None
#     # return match.group(2) if match else None


# def get_embed_url(doc_id):
#     """
#     Builds the Scribd embed URL for the given document ID.
#     """
#     return f"https://www.scribd.com/embeds/{doc_id}/content"


# def setup_driver():
#     options = Options()
#     # options.add_argument('--headless=new')  # Uncomment to run headless
#     options.add_argument('--disable-gpu')
#     options.add_argument('--no-sandbox')
#     options.add_argument('--log-level=3')
#     options.add_argument('--window-size=1920,1080')
#     options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
#     return webdriver.Chrome(options=options)


# def fetch_pdf_bytes(driver, embed_url, scale=0.98):
#     """
#     Navigates to the embed URL, applies cleanup, and returns PDF bytes.
#     """
#     driver.get(embed_url)

#     # Wait for the Scribd container to load
#     timeout = time.time() + 30
#     while time.time() < timeout:
#         try:
#             outer = driver.find_element(By.CLASS_NAME, "outer_page_container")
#             if outer:
#                 break
#         except:
#             time.sleep(0.5)
#     else:
#         raise TimeoutError("Document did not load in time.")

#     # Cleanup and force page breaks
#     driver.execute_script("""
#         const outer = document.querySelector('div.outer_page_container');
#         document.body.innerHTML = '';
#         document.body.appendChild(outer);
#         document.body.style.margin = '0';

#         const pages = outer.querySelectorAll('div.page');
    
#         });
#     """)

#     time.sleep(1)
#     result = driver.execute_cdp_cmd("Page.printToPDF", {
#         "printBackground": True,
#         "paperWidth": 8.27,
#         "paperHeight": 11.69,
#         "marginTop": 0,
#         "marginBottom": 0,
#         "marginLeft": 0,
#         "marginRight": 0,
#         "preferCSSPageSize": True,
#         "scale": scale
#     })

#     return base64.b64decode(result['data'])


# def trim_and_save(pdf_bytes, output_path):
#     """
#     Removes blank pages from PDF bytes and writes trimmed PDF to disk.
#     """
#     reader = PdfReader(io.BytesIO(pdf_bytes))
#     writer = PdfWriter()

#     for idx, page in enumerate(reader.pages, start=1):
#         text = page.extract_text()
#         if text and text.strip():
#             writer.add_page(page)
#         else:
#             print(f"[i] Skipping blank page {idx}")

#     with open(output_path, 'wb') as f:
#         writer.write(f)

#     print(f"[+] Saved trimmed PDF: {output_path}")


# def scrape_scribd_list(urls):
#     """
#     Processes a list of Scribd URLs, saving trimmed PDFs named by document ID.
#     """
#     driver = setup_driver()
#     for url in urls:
#         doc_id = extract_doc_id(url)
#         if not doc_id:
#             print(f"[-] Could not extract doc ID from URL: {url}")
#             continue

#         try:
#             embed_url = get_embed_url(doc_id)
#             print(f"[+] Processing doc {doc_id}...")
#             pdf_bytes = fetch_pdf_bytes(driver, embed_url)
#             output_file = f"{doc_id}.pdf"
#             trim_and_save(pdf_bytes, output_file)
#         except Exception as e:
#             print(f"[-] Error processing {doc_id}: {e}")

#     driver.quit()


# if __name__ == "__main__":
#     # Example batch list
#     scribd_urls = [
#         "https://www.scribd.com/document/466329148/requestDocumentResultPage",
#         "https://www.scribd.com/presentation/513168371/ABN",
#         # Add more URLs here
#     ]
#     scrape_scribd_list(scribd_urls)
