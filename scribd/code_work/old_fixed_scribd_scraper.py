import asyncio
import os
import re
import logging
import time
import base64
import io
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
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        driver = webdriver.Chrome(options=options)
        return driver

    def extract_doc_id(self, scribd_url):
        match = re.search(r'/[\w\-]+/(\d+)', scribd_url)
        return match.group(1) if match else None

    def get_embed_url(self, doc_id):
        if not doc_id:
            raise ValueError("Document ID cannot be None or empty.")
        return f"https://www.scribd.com/embeds/{doc_id}/content"

    async def search_google_for_scribd(self, query, max_documents=10):
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
                    search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num=30"
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
                    
                    if len(all_document_urls) >= max_documents:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Search error for query '{search_query}': {e}")
            
            await browser.close()
            self.logger.info(f"Found {len(all_document_urls)} Scribd documents in {time.time() - start_time:.2f} seconds")
            return all_document_urls[:max_documents]

    def print_page_to_pdf_bytes(self, driver, embed_url):
        self.logger.info(f"Navigating to {embed_url}")
        driver.get(embed_url)
        timeout = time.time() + 30
        while True:
            try:
                outer = driver.find_element(By.CLASS_NAME, "outer_page_container")
                if outer:
                    break
            except:
                pass
            if time.time() > timeout:
                raise TimeoutError("Timeout waiting for Scribd document to load.")
            time.sleep(1)
        
        driver.execute_script("""
            const outer = document.querySelector('div.outer_page_container');
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
        """)
        time.sleep(1)
        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "paperWidth": 8.27,
            "paperHeight": 11.69,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "preferCSSPageSize": True,
            "scale": 0.98
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
            return
        embed_url = self.get_embed_url(doc_id)
        driver = self.setup_driver()
        try:
            self.logger.info(f"[{index+1}] Processing doc_id {doc_id}")
            pdf_bytes = self.print_page_to_pdf_bytes(driver, embed_url)
            filename = f"{self.query.replace(' ', '_')}_{doc_id}.pdf"
            output_path = os.path.join(self.SAVE_FOLDER, filename)
            self.trim_and_save(pdf_bytes, output_path)
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
        finally:
            driver.quit()

    async def run(self, query, max_docs=3):
        self.query = query
        self.logger.info(f"Starting scraping process for query: '{query}' with max_docs: {max_docs}")
        urls = await self.search_google_for_scribd(query, max_docs)
        if not urls:
            self.logger.warning("No Scribd documents found.")
            print("No Scribd documents found.")
            return
        
        self.logger.info(f"Found {len(urls)} documents to process")
        for i, url in enumerate(urls):
            self.logger.info(f"Processing document {i+1}/{len(urls)}: {url}")
            self.scrape_and_save_pdf(url, i)  # Pass the index, not filename
            if i < len(urls) - 1:
                self.logger.info("Waiting 5 seconds before next download...")
                time.sleep(5)
        
        self.logger.info("Scraping process completed successfully")

if __name__ == "__main__":
    async def main():
        scraper = ScribdScraper()
        await scraper.run("australia tax file number", max_docs=5)
    asyncio.run(main())
