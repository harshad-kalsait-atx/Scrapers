import asyncio
import os
import re
import logging
import time
import base64
import io
import json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from playwright.async_api import async_playwright
from PyPDF2 import PdfReader, PdfWriter

class ScribdScraper:
    def __init__(self):
        self.query = None
        self.start_time = datetime.now()
        self.SAVE_FOLDER = "scraped_data/scribd_documents"
        self.LOG_FOLDER = "logs"
        os.makedirs(self.LOG_FOLDER, exist_ok=True)
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)
        self.logger = self.setup_logging()
        self.processed_doc_ids = set()  # Track processed doc_ids in current session

    def setup_logging(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(self.LOG_FOLDER, f"scribd_scraper_{timestamp}.log")
        logger = logging.getLogger('ScribdScraper')
        logger.setLevel(logging.DEBUG)
        logger.handlers = []
        file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.info(f"Logging started - Log file: {log_filename}")
        logger.info(f"Script started at {datetime.now()}")
        return logger

    def setup_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--print-to-pdf-no-header')
        
        # Add printing preferences similar to youtube_scribd_2.py
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
        }
        options.add_experimental_option('prefs', prefs)
        options.add_argument('--kiosk-printing')
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        driver = webdriver.Chrome(options=options)
        return driver

    def check_doc_id_exists(self, doc_id, query):
        """
        Check if doc_id already exists in:
        1. Current session memory
        2. Existing PDF files in save folder
        3. Previous log files
        """
        # Check current session
        if doc_id in self.processed_doc_ids:
            self.logger.info(f"Doc_id {doc_id} already processed in current session - skipping")
            return True
        
        # Check existing PDF files
        query_clean = query.replace(' ', '_')
        pattern = f"{query_clean}_{doc_id}.pdf"
        existing_files = os.listdir(self.SAVE_FOLDER)
        for filename in existing_files:
            if filename == pattern or filename.endswith(f"_{doc_id}.pdf"):
                self.logger.info(f"Doc_id {doc_id} already exists as file: {filename} - skipping")
                return True
        
        # Check previous log files for this doc_id
        log_files = [f for f in os.listdir(self.LOG_FOLDER) if f.startswith("scribd_scraper_") and f.endswith(".log")]
        for log_file in log_files:
            try:
                with open(os.path.join(self.LOG_FOLDER, log_file), 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    # Look for successful processing patterns
                    success_patterns = [
                        f"Processing doc_id {doc_id}",
                        f"Saved trimmed PDF: .*{doc_id}.pdf",
                        f"PDF saved to .*{doc_id}.pdf"
                    ]
                    for pattern in success_patterns:
                        if re.search(pattern, log_content):
                            self.logger.info(f"Doc_id {doc_id} found in previous logs ({log_file}) - skipping")
                            return True
            except Exception as e:
                self.logger.debug(f"Error reading log file {log_file}: {e}")
        
        return False

    def extract_doc_id(self, scribd_url):
        match = re.search(r'/document/(\d+)', scribd_url)
        return match.group(1) if match else None

    def mark_doc_id_processed(self, doc_id):
        """Mark doc_id as processed in current session"""
        self.processed_doc_ids.add(doc_id)
        self.logger.debug(f"Marked doc_id {doc_id} as processed")

    def get_embed_url(self, doc_id):
        if not doc_id:
            raise ValueError("Document ID cannot be None or empty.")
        return f"https://www.scribd.com/embeds/{doc_id}/content"

    async def search_google_for_scribd(self, query, max_documents=10, max_search_results=50):
        self.logger.info(f"Starting Google search for query: '{query}', max_documents: {max_documents}")
        start_time = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage'])
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            page = await context.new_page()
            
            # Use multiple search strategies like the working version
            search_queries = [f"{query} site:scribd.com", f'"{query}" site:scribd.com']
            all_document_urls = []
            
            for search_query in search_queries:
                try:
                    # Increase search results to have more candidates
                    search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num={max_search_results}"
                    await page.goto(search_url, wait_until='networkidle', timeout=20000)
                    await page.wait_for_timeout(2000)
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links:
                        href = link.get('href')
                        if href and 'scribd.com/document/' in href:
                            if '/url?q=' in href:
                                actual_url = href.split('/url?q=')[1].split('&')[0]
                                actual_url = unquote(actual_url)
                            else:
                                actual_url = href
                            clean_url = actual_url.split('?')[0].split('#')[0]
                            if clean_url not in all_document_urls:
                                all_document_urls.append(clean_url)
                                self.logger.info(f"Found Scribd document: {clean_url}")
                    
                    if len(all_document_urls) >= max_search_results:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Search error for query '{search_query}': {e}")
            
            await browser.close()
            self.logger.info(f"Found {len(all_document_urls)} total Scribd documents in {time.time() - start_time:.2f} seconds")
            return all_document_urls

    def print_page_to_pdf_bytes(self, driver, embed_url):
        self.logger.info(f"Navigating to {embed_url}")
        driver.get(embed_url)
        time.sleep(3)  # Initial wait for page load
        
        # Wait for document to load with better timeout handling
        timeout = time.time() + 30
        while True:
            try:
                # Try both selectors to be more robust
                outer = driver.find_element(By.CLASS_NAME, "outer_page_container")
                if outer:
                    self.logger.info("Document container found")
                    break
            except:
                try:
                    # Alternative selector
                    pages = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
                    if pages:
                        self.logger.info("Document pages found")
                        break
                except:
                    pass
            if time.time() > timeout:
                raise TimeoutError("Timeout waiting for Scribd document to load.")
            time.sleep(1)
        
        # Scroll through all pages to ensure they're loaded (from youtube_scribd_2.py)
        self.logger.info("Scrolling through pages to load content...")
        pages = driver.find_elements(By.CSS_SELECTOR, "[class*='page']")
        for i, page in enumerate(pages):
            driver.execute_script("arguments[0].scrollIntoView();", page)
            time.sleep(0.3)
        self.logger.info(f"Finished scrolling through {len(pages)} pages")
        
        # Remove unwanted elements (improved from youtube_scribd_2.py)
        self.logger.info("Cleaning up unwanted elements...")
        driver.execute_script("""
            // Remove toolbars and navigation elements
            let top = document.querySelector('.toolbar_top');
            if (top) top.remove();
            let bottom = document.querySelector('.toolbar_bottom');
            if (bottom) bottom.remove();
            let scrollers = document.querySelectorAll('.document_scroller');
            scrollers.forEach(el => el.className = '');
            
            // Try to isolate the main content
            const outer = document.querySelector('div.outer_page_container');
            if (outer) {
                document.body.innerHTML = '';
                document.body.appendChild(outer);
                document.body.style.margin = '0';
                const pages = outer.querySelectorAll('div.page');
                pages.forEach(p => {
                    p.style.pageBreakAfter = 'always';
                    p.style.breakAfter = 'page';
                    p.style.margin = '0';
                    p.style.padding = '0';
                });
            }
        """)
        time.sleep(1)
        
        self.logger.info("Generating PDF...")
        result = driver.execute_cdp_cmd("Page.printToPDF", {
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
        return base64.b64decode(result['data'])

    def trim_and_save(self, pdf_bytes, output_path):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                writer.add_page(page)
            else:
                self.logger.info(f"[i] Skipping blank page {idx}")
        with open(output_path, 'wb') as f:
            writer.write(f)
        self.logger.info(f"[+] Saved trimmed PDF: {output_path}")

    def scrape_and_save_pdf(self, url, index):
        doc_id = self.extract_doc_id(url)
        if not doc_id:
            self.logger.error(f"Could not extract doc_id from URL: {url}")
            return False
        
        # Check if document already exists
        if self.check_doc_id_exists(doc_id, self.query):
            self.logger.info(f"[{index+1}] Skipping doc_id {doc_id} - already processed")
            return False
        
        # Mark as being processed
        self.mark_doc_id_processed(doc_id)
        
        embed_url = self.get_embed_url(doc_id)
        driver = self.setup_driver()
        try:
            self.logger.info(f"[{index+1}] Processing doc_id {doc_id}")
            pdf_bytes = self.print_page_to_pdf_bytes(driver, embed_url)
            filename = f"{self.query.replace(' ', '_')}_{doc_id}.pdf"
            output_path = os.path.join(self.SAVE_FOLDER, filename)
            self.trim_and_save(pdf_bytes, output_path)
            self.logger.info(f"[{index+1}] Successfully processed and saved doc_id {doc_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to download {url} (doc_id: {doc_id}): {e}")
            # Remove from processed set if failed
            self.processed_doc_ids.discard(doc_id)
            return False
        finally:
            driver.quit()

    async def run(self, query, max_docs=3):
        self.query = query
        self.logger.info(f"Starting scraping process for query: '{query}' with max_docs: {max_docs}")
        
        # Get more URLs than needed to account for duplicates
        search_buffer = max_docs * 3  # Search for 3x more documents to handle duplicates
        urls = await self.search_google_for_scribd(query, max_docs, max_search_results=search_buffer)
        
        if not urls:
            self.logger.warning("No Scribd documents found.")
            print("No Scribd documents found.")
            return
        
        self.logger.info(f"Found {len(urls)} total documents to check")
        processed_count = 0
        skipped_count = 0
        target_docs = max_docs
        
        for i, url in enumerate(urls):
            # Stop if we've already processed the required number of documents
            if processed_count >= target_docs:
                self.logger.info(f"Target of {target_docs} documents reached. Stopping search.")
                break
                
            self.logger.info(f"Checking document {i+1}/{len(urls)}: {url}")
            success = self.scrape_and_save_pdf(url, processed_count)  # Use processed_count for indexing
            
            if success:
                processed_count += 1
                self.logger.info(f"Progress: {processed_count}/{target_docs} documents processed")
                
                # Only wait if we have more documents to process and haven't reached target
                if processed_count < target_docs and i < len(urls) - 1:
                    self.logger.info("Waiting 5 seconds before next download...")
                    time.sleep(5)
            else:
                skipped_count += 1
                self.logger.info(f"Continuing search... ({processed_count}/{target_docs} processed, {skipped_count} skipped)")
        
        # Final summary
        if processed_count < target_docs:
            self.logger.warning(f"Could only process {processed_count}/{target_docs} new documents. {skipped_count} were duplicates.")
            print(f"Warning: Only found {processed_count} new documents out of {target_docs} requested. {skipped_count} duplicates were skipped.")
        else:
            self.logger.info(f"Successfully processed {processed_count}/{target_docs} new documents. {skipped_count} duplicates were skipped.")
            print(f"Success: Processed {processed_count} new documents. {skipped_count} duplicates were skipped.")
        
        self.logger.info(f"Scraping process completed: {processed_count} processed, {skipped_count} skipped")

if __name__ == "__main__":
    async def main():
        scraper = ScribdScraper()
        await scraper.run("Australia medicare number scribd", max_docs=100)
    asyncio.run(main())
