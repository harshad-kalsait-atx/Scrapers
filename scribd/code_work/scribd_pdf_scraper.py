# Still has issue with blank pages in the PDF.

import asyncio
import os
import re
import logging
import time
import base64
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        driver = webdriver.Chrome(options=options)
        return driver

    def print_page_to_pdf(self, driver, output_path):
        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "paperWidth": 8.27,
            "paperHeight": 11.69,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "preferCSSPageSize": True
        })
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(result['data']))
        self.logger.info(f"PDF saved to {output_path}")

    def get_embed_url(self, scribd_url):
        doc_id = scribd_url.split("/document/")[1].split("/")[0]
        return f"https://www.scribd.com/embeds/{doc_id}/content"

    async def search_google_for_scribd(self, query, max_documents=10):
        self.logger.info(f"Starting Google search for query: '{query}', max_documents: {max_documents}")
        start_time = time.time()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage'])
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            page = await context.new_page()
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
                    if len(all_document_urls) >= max_documents:
                        break
                except Exception as e:
                    self.logger.error(f"Search error: {e}")
            await browser.close()
            return all_document_urls[:max_documents]

    def scrape_scribd_to_pdf(self, scribd_url, output_pdf):
        embed_url = self.get_embed_url(scribd_url)
        driver = self.setup_driver()
        try:
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
                    self.logger.error("Timeout waiting for document")
                    driver.quit()
                    return
                time.sleep(1)
            driver.execute_script("""
                const outer = document.querySelector('div.outer_page_container');
                document.body.innerHTML = '';
                document.body.appendChild(outer);
                document.body.style.margin = '0';
            """)
            time.sleep(1)
            self.print_page_to_pdf(driver, output_pdf)
        except Exception as e:
            self.logger.error(f"Error scraping Scribd: {e}", exc_info=True)
        finally:
            driver.quit()

    async def run(self, query, max_docs=3):
        self.query = query
        urls = await self.search_google_for_scribd(query, max_docs)
        if not urls:
            print("No Scribd documents found.")
            return
        for i, url in enumerate(urls):
            filename = os.path.join(self.SAVE_FOLDER, f"{query.replace(' ', '_')}_{i + 1}.pdf")
            self.scrape_scribd_to_pdf(url, filename)
            if i < len(urls) - 1:
                time.sleep(5)

if __name__ == "__main__":
    async def main():
        scraper = ScribdScraper()
        await scraper.run("australia medicare card", max_docs=3)
    asyncio.run(main())
