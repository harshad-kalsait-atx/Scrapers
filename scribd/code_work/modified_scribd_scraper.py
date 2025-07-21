#Complete Working code but updates required (wait until the full pdf loaded,naming also required)

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

# Selenium imports for download functionality
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class ScribdScraper:
    def __init__(self):
        self.query = None
        self.start_time = datetime.now()
        self.SAVE_FOLDER = "scraped_data/scribd_documents"
        self.LOG_FOLDER = "logs"
        os.makedirs(self.LOG_FOLDER, exist_ok=True)
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)
        self.downloaded_files = set()
        self.logger = self.setup_logging()

    def setup_logging(self):
        """Setup detailed logging configuration"""
        # Create timestamp for log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(self.LOG_FOLDER, f"scribd_scraper_{timestamp}.log")
        
        # Create logger
        logger = logging.getLogger('ScribdScraper')
        logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        logger.handlers = []
        
        # Create file handler with detailed formatting
        file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create detailed formatter for file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create simple formatter for console
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Log the start of the session
        logger.info(f"Logging started - Log file: {log_filename}")
        logger.info(f"Script started at {datetime.now()}")
        
        return logger

    def extract_scribd_info(self, scribd_url):
        """Extract document ID and title from Scribd URL"""
        self.logger.debug(f"Extracting info from URL: {scribd_url}")
        
        pattern = r'https://www\.scribd\.com/(?:document|doc|presentation)/(\d+)/([^/?]+)'
        match = re.search(pattern, scribd_url)
        
        if match:
            doc_id = match.group(1)
            doc_title = match.group(2)
            self.logger.info(f"Successfully extracted - ID: {doc_id}, Title: {doc_title}")
            return doc_id, doc_title
        else:
            self.logger.error(f"Could not extract info from URL: {scribd_url}")
            print(f"Could not extract info from URL: {scribd_url}")
            return None, None

    def get_embed_url(self, scribd_url):
        """
        Converts normal Scribd document URL to embed URL.
        """
        self.logger.debug(f"Converting to embed URL: {scribd_url}")
        doc_id = scribd_url.split("/document/")[1].split("/")[0]
        
        embed_url = f"https://www.scribd.com/embeds/{doc_id}/content"
        self.logger.debug(f"Generated embed URL: {embed_url}")
        return embed_url

    async def search_google_for_scribd(self, query, max_documents=10):
        """Google search for Scribd documents - balanced speed/reliability"""
        self.logger.info(f"Starting Google search for query: '{query}', max_documents: {max_documents}")
        
        start_time = time.time()
        
        async with async_playwright() as p:
            self.logger.debug("Launching Playwright browser")
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-images',  # Keep this for faster loading
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            self.logger.debug("Browser context and page created")
            
            # Keep the original search strategies but optimize
            search_queries = [
                f"{query} site:scribd.com",
                f'"{query}" site:scribd.com'
            ]
            self.logger.debug(f"Search queries prepared: {search_queries}")
            
            all_document_urls = []
            
            for search_query in search_queries:
                try:
                    search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num=30"
                    self.logger.info(f"Searching: {search_query}")
                    self.logger.debug(f"Search URL: {search_url}")
                    print(f"Searching: {search_query}")
                    
                    await page.goto(search_url, wait_until='networkidle', timeout=20000)
                    await page.wait_for_timeout(2000)
                    self.logger.debug("Page loaded successfully")
                    
                    # Optimized scrolling
                    for i in range(3):
                        self.logger.debug(f"Scrolling iteration {i+1}/3")
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(1500)
                        
                        try:
                            show_more = page.locator('input[value="Show more results"]')
                            if await show_more.is_visible():
                                self.logger.debug("Clicking 'Show more results' button")
                                await show_more.click()
                                await page.wait_for_timeout(2000)
                        except Exception as e:
                            self.logger.debug(f"No 'Show more results' button found: {e}")
                            pass
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    self.logger.debug("Page content parsed with BeautifulSoup")
                    
                    all_links = soup.find_all('a', href=True)
                    self.logger.debug(f"Found {len(all_links)} total links on page")
                    
                    initial_count = len(all_document_urls)
                    
                    for link in all_links:
                        href = link.get('href')
                        if href and 'scribd.com' in href:
                            if '/url?q=' in href:
                                actual_url = href.split('/url?q=')[1].split('&')[0]
                                actual_url = unquote(actual_url)
                            elif href.startswith('/search?'):
                                continue
                            else:
                                actual_url = href
                            
                            if re.search(r'scribd\.com/(?:document|doc|presentation)/\d+', actual_url):
                                clean_url = actual_url.split('?')[0].split('#')[0]
                                if clean_url not in all_document_urls:
                                    all_document_urls.append(clean_url)
                                    self.logger.debug(f"Added Scribd URL: {clean_url}")
                    
                    new_count = len(all_document_urls) - initial_count
                    self.logger.info(f"Found {new_count} new Scribd documents from query: {search_query}")
                    
                    if len(all_document_urls) >= max_documents:
                        self.logger.info(f"Reached maximum documents limit ({max_documents})")
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error with search query '{search_query}': {e}", exc_info=True)
                    print(f"Error with search query '{search_query}': {e}")
                    continue
            
            await browser.close()
            self.logger.debug("Browser closed")
            
            unique_urls = list(dict.fromkeys(all_document_urls))  # Remove duplicates faster
            search_time = time.time() - start_time
            
            self.logger.info(f"Search completed in {search_time:.2f} seconds")
            self.logger.info(f"Found {len(unique_urls)} unique Scribd documents")
            print(f"Found {len(unique_urls)} unique Scribd documents")
            
            final_urls = unique_urls[:max_documents]
            self.logger.debug(f"Returning {len(final_urls)} URLs: {final_urls}")
            
            return final_urls

    def setup_selenium_driver(self, show_browser=False):
        """Setup Selenium driver for PDF generation"""
        self.logger.debug(f"Setting up Selenium driver - show_browser: {show_browser}")
        
        options = Options()
        
        if not show_browser:
            options.add_argument('--headless=new')  # Use new headless mode for print-to-PDF
            self.logger.debug("Browser set to headless mode")
        
        # Essential arguments for PDF generation
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Enable performance logging for CDP
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("Selenium Chrome driver created successfully")
            return driver
        except Exception as e:
            self.logger.error(f"Failed to create Selenium driver: {e}", exc_info=True)
            raise

    def print_page_to_pdf(self, driver, output_path):
        """
        Uses Chrome DevTools Protocol to print the current page to PDF.
        """
        self.logger.debug(f"Printing page to PDF: {output_path}")
        
        try:
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
            
            self.logger.info(f"PDF successfully created: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error printing to PDF: {e}", exc_info=True)
            return False

    def download_document_selenium(self, scribd_url, doc_id, doc_title, query, index, show_browser=False):
        """Download document using new embed URL approach"""
        self.logger.info(f"Starting download for document {index+1} - ID: {doc_id}, Title: {doc_title}")
        
        driver = None
        download_start_time = time.time()
        
        try:
            # Get embed URL
            embed_url = self.get_embed_url(scribd_url)
            
            # Setup driver
            driver = self.setup_selenium_driver(show_browser)
            
            self.logger.debug(f"Navigating to embed URL: {embed_url}")
            print(f"[+] Navigating to {embed_url}")
            driver.get(embed_url)

            # Wait for outer_page_container to load
            self.logger.debug("Waiting for document to load...")
            timeout = time.time() + 30
            outer_container = None
            
            while True:
                try:
                    outer_container = driver.find_element(By.CLASS_NAME, "outer_page_container")
                    if outer_container:
                        self.logger.debug("Document container found")
                        break
                except:
                    pass
                    
                if time.time() > timeout:
                    self.logger.error("Timeout waiting for document to load")
                    print("[-] Timeout waiting for document.")
                    return False
                    
                time.sleep(1)

            print("[+] Document loaded. Cleaning page...")
            self.logger.debug("Cleaning page content...")

            # Inject JS to remove all elements except the outer_page_container
            driver.execute_script("""
                const outer = document.querySelector('div.outer_page_container');
                document.body.innerHTML = '';
                document.body.appendChild(outer);
                document.body.style.margin = '0';
            """)

            time.sleep(1)  # Wait for styles to apply

            # Generate filename
            new_filename = f"{query.replace(' ', '_')}_{index + 1}.pdf"
            new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename)  # Clean filename
            output_path = os.path.join(self.SAVE_FOLDER, new_filename)

            print(f"[+] Printing to {new_filename}")
            self.logger.debug(f"Generating PDF: {output_path}")
            
            # Print to PDF
            if self.print_page_to_pdf(driver, output_path):
                # Check if file was created successfully
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    file_size = os.path.getsize(output_path)
                    download_time = time.time() - download_start_time
                    
                    self.logger.info(f"Download completed successfully in {download_time:.2f} seconds")
                    self.logger.info(f"File size: {file_size} bytes")
                    
                    print(f"[+] Done. Downloaded: {new_filename}")
                    print(f"File size: {file_size} bytes")
                    
                    return True
                else:
                    self.logger.error("PDF file was not created or is empty")
                    print("[-] PDF file was not created or is empty")
                    return False
            else:
                self.logger.error("Failed to generate PDF")
                print("[-] Failed to generate PDF")
                return False

        except Exception as e:
            download_time = time.time() - download_start_time
            self.logger.error(f"Download error after {download_time:.2f} seconds: {e}", exc_info=True)
            print(f"[-] Download error: {e}")
            return False
            
        finally:
            if driver:
                try:
                    self.logger.debug("Closing Selenium driver")
                    driver.quit()
                except Exception as e:
                    self.logger.error(f"Error closing driver: {e}")

    async def run(self, query, max_docs=3, show_browser=False):
        """Main run method to execute the scraping process"""
        self.query = query
        print(f"[ScribdScraper] Searching documents for '{query}' ...")
        
        urls = await self.search_google_for_scribd(query, max_docs)
        if not urls:
            print("No Scribd documents found.")
            return

        successful_downloads = 0
        for i, url in enumerate(urls):
            doc_id, doc_title = self.extract_scribd_info(url)
            if not doc_id or not doc_title:
                print(f"Invalid URL: {url}")
                continue

            success = self.download_document_selenium(url, doc_id, doc_title, query, i, show_browser)
            if success:
                successful_downloads += 1
                
            # Add delay between downloads
            if i < len(urls) - 1:
                print("Waiting 5 seconds before next download...")
                time.sleep(5)

        print(f"\n[ScribdScraper] Completed! Successfully downloaded {successful_downloads} out of {len(urls)} documents.")
        self.logger.info(f"Scraping session completed - {successful_downloads}/{len(urls)} successful downloads")

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        scraper = ScribdScraper()
        await scraper.run("Austalian tax file number", max_docs=3, show_browser=False)
    
    asyncio.run(main())