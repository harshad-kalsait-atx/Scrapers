# This code works well.
# In this code ,there is flaw that we found URL after lots of extarction process and after that some of them are 
# gets skipped because that URL is already processed. Beacause of this flaw, we are not able to get all the pins count as input.
# We have fixed this flaw in the new code scriot "pinterest_scraper_optimized_2.py"
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


import os
import re
import requests
import urllib.parse
import json
import logging
from datetime import datetime
from time import sleep
from playwright.sync_api import sync_playwright

class PinterestScraper:
    def __init__(self):
        self.SAVE_FOLDER = "Pintrest_data"
        self.LOG_FOLDER = "logs"
        self.PROCESSED_PINS_FILE = "processed_pins.json"
        
        # Create directories
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)
        os.makedirs(self.LOG_FOLDER, exist_ok=True)
        
        # Initialize logging
        self.setup_logging()
        
        # Load processed pins history
        self.processed_pins = self.load_processed_pins()
        
        # Initialize session
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25)
        self.session.mount("https://", adapter)
        
        # Statistics
        self.stats = {
            'main_pins_found': 0,
            'similar_pins_found': 0,
            'total_unique_pins': 0,
            'successful_downloads': 0,
            'skipped_duplicates': 0,
            'failed_downloads': 0
        }
        
        self.logger.info("Pinterest Multi-Level Scraper initialized")
        self.logger.info(f"Found {len(self.processed_pins)} previously processed pins")

    def setup_logging(self):
        """Setup logging configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"pinterest_multilevel_{timestamp}.log"
        log_path = os.path.join(self.LOG_FOLDER, log_filename)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger('PinterestMultiLevelScraper')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging initialized. Log file: {log_path}")

    def load_processed_pins(self):
        """Load previously processed pin IDs from file"""
        try:
            if os.path.exists(self.PROCESSED_PINS_FILE):
                with open(self.PROCESSED_PINS_FILE, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded {len(data)} processed pins from history")
                    return set(data)
            else:
                self.logger.info("No previous processed pins history found")
                return set()
        except Exception as e:
            self.logger.error(f"Error loading processed pins: {e}")
            return set()

    def save_processed_pins(self):
        """Save processed pin IDs to file"""
        try:
            with open(self.PROCESSED_PINS_FILE, 'w') as f:
                json.dump(list(self.processed_pins), f, indent=2)
            self.logger.debug(f"Saved {len(self.processed_pins)} processed pins to history")
        except Exception as e:
            self.logger.error(f"Error saving processed pins: {e}")

    def extract_pin_id_from_url(self, pin_url):
        """Extract pin ID from full URL with multiple pattern support"""
        self.logger.debug(f"Extracting pin ID from URL: {pin_url}")
        
        # Pattern 1: Standard /pin/ID format
        match = re.search(r'/pin/(\d{10,20})', pin_url)
        if match:
            pin_id = match.group(1)
            self.logger.debug(f"Extracted pin ID (standard format): {pin_id}")
            return pin_id
        
        # Pattern 2: /pin/description--ID format (with double dash)
        match = re.search(r'/pin/[^/]*--(\d{10,20})/?', pin_url)
        if match:
            pin_id = match.group(1)
            self.logger.debug(f"Extracted pin ID (description format): {pin_id}")
            return pin_id
        
        # Pattern 3: /pin/description-ID format (with single dash)
        match = re.search(r'/pin/[^/]*-(\d{10,20})/?', pin_url)
        if match:
            pin_id = match.group(1)
            self.logger.debug(f"Extracted pin ID (single dash format): {pin_id}")
            return pin_id
        
        # Pattern 4: Extract any long number sequence from the URL
        match = re.search(r'(\d{10,20})', pin_url)
        if match:
            pin_id = match.group(1)
            self.logger.debug(f"Extracted pin ID (fallback pattern): {pin_id}")
            return pin_id
        
        self.logger.warning(f"Could not extract pin ID from URL: {pin_url}")
        return None

    def is_pin_already_processed(self, pin_id):
        """Check if pin ID was already processed"""
        is_processed = pin_id in self.processed_pins
        if is_processed:
            self.logger.debug(f"Pin {pin_id} already processed - skipping")
        return is_processed

    def mark_pin_as_processed(self, pin_id):
        """Mark pin ID as processed"""
        self.processed_pins.add(pin_id)
        self.save_processed_pins()
        self.logger.debug(f"Marked pin {pin_id} as processed")

    def wait_for_page_load(self, page, timeout=45):
        """Wait for page to be fully loaded"""
        self.logger.debug("Waiting for page to be fully loaded...")
        
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            self.logger.debug("DOM content loaded")
            
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
                self.logger.debug("Network idle achieved")
            except Exception as e:
                self.logger.debug(f"Network idle timeout: {e}")
            
            selectors_to_try = [
                "div[data-test-id='pin']",
                "div[data-test-id='pinWrapper']", 
                "div[role='button']",
                "img[alt]",
                "a[href*='/pin/']"
            ]
            
            selector_found = False
            for selector in selectors_to_try:
                try:
                    page.wait_for_selector(selector, state="attached", timeout=10000)
                    self.logger.debug(f"Found selector: {selector}")
                    selector_found = True
                    break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} not found: {e}")
                    continue
            
            if not selector_found:
                self.logger.warning("No Pinterest-specific selectors found, continuing anyway")
            
            sleep(2)
            self.logger.debug("Page loading complete")
            return True
            
        except Exception as e:
            self.logger.warning(f"Page load wait error: {e}")
            sleep(3)
            return False

    def get_main_pins_from_search(self, keyword, count=30):
        """Get main pins from Pinterest search with 25% zoom"""
        self.logger.info(f"🔍 STEP 1: Getting {count} main pins for keyword: '{keyword}'")
        print(f"🔍 STEP 1: Searching for main pins - keyword: '{keyword}'")
        
        search_term = urllib.parse.quote_plus(keyword)
        search_url = f"https://www.pinterest.com/search/pins/?q={search_term}"
        self.logger.debug(f"Search URL: {search_url}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.logger.info("Navigating to search page")
                page.goto(search_url, timeout=30000)
                
                # Set zoom to 25% for better visibility
                self.logger.info("Setting page zoom to 25%")
                page.evaluate("document.body.style.zoom = '0.25'")
                print("🔍 Set page zoom to 25% for better pin visibility")
                
                self.logger.info("Waiting for page to fully load...")
                print("⏳ Waiting for page to fully load...")
                self.wait_for_page_load(page)
                
                sleep(3)
                
                # Scroll to load more pins
                scroll_count = 0
                max_scrolls = 20
                previous_pin_count = 0
                stable_count = 0
                
                while len(page.locator("a[href^='/pin/']").all()) < count and scroll_count < max_scrolls:
                    scroll_count += 1
                    current_pins = len(page.locator("a[href^='/pin/']").all())
                    
                    self.logger.debug(f"Scrolling to load more pins (scroll #{scroll_count})")
                    page.mouse.wheel(0, 5000)
                    sleep(3)
                    
                    new_pin_count = len(page.locator("a[href^='/pin/']").all())
                    
                    if new_pin_count == previous_pin_count:
                        stable_count += 1
                        if stable_count >= 3:
                            self.logger.debug("No new pins loading, stopping scroll")
                            break
                    else:
                        stable_count = 0
                    
                    previous_pin_count = new_pin_count
                    
                    self.logger.debug(f"Current pins found: {new_pin_count}")
                    print(f"   📌 Found {new_pin_count} pins so far...")
                    
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass

                # Extract pin URLs
                self.logger.debug("Extracting main pin URLs from search page")
                anchors = page.locator("a[href^='/pin/']").all()
                main_pin_urls = []
                seen_ids = set()
                
                for a in anchors:
                    href = a.get_attribute("href")
                    if href:
                        full_url = urllib.parse.urljoin("https://www.pinterest.com", href)
                        pin_id = self.extract_pin_id_from_url(full_url)
                        
                        if pin_id and pin_id not in seen_ids:
                            seen_ids.add(pin_id)
                            main_pin_urls.append(full_url)
                            
                        if len(main_pin_urls) >= count:
                            break

                self.stats['main_pins_found'] = len(main_pin_urls)
                self.logger.info(f"✅ Successfully extracted {len(main_pin_urls)} main pin URLs")
                print(f"✅ Found {len(main_pin_urls)} main pins")
                
                return main_pin_urls
                
            except Exception as e:
                self.logger.error(f"Error during main pin search: {e}")
                return []
            finally:
                browser.close()

    def get_similar_pins_from_pin_page(self, pin_url, count=30):
        """Get similar pins from a specific pin page"""
        pin_id = self.extract_pin_id_from_url(pin_url)
        self.logger.debug(f"Getting similar pins from pin {pin_id}")
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.logger.debug(f"Navigating to pin page: {pin_url}")
                page.goto(pin_url, timeout=30000)
                
                page.evaluate("document.body.style.zoom = '0.25'")
                self.wait_for_page_load(page)
                
                scroll_count = 0
                max_scrolls = 15
                similar_pins = []
                previous_similar_count = 0
                stable_count = 0
                
                while len(similar_pins) < count and scroll_count < max_scrolls:
                    scroll_count += 1
                    page.mouse.wheel(0, 4000)
                    sleep(2)
                    
                    anchors = page.locator("a[href^='/pin/']").all()
                    seen_ids = set()
                    current_similar_pins = []
                    
                    for a in anchors:
                        href = a.get_attribute("href")
                        if href:
                            full_url = urllib.parse.urljoin("https://www.pinterest.com", href)
                            similar_pin_id = self.extract_pin_id_from_url(full_url)
                            
                            if similar_pin_id and similar_pin_id != pin_id and similar_pin_id not in seen_ids:
                                seen_ids.add(similar_pin_id)
                                current_similar_pins.append(full_url)
                    
                    for pin in current_similar_pins:
                        if pin not in similar_pins:
                            similar_pins.append(pin)
                            if len(similar_pins) >= count:
                                break
                    
                    if len(similar_pins) == previous_similar_count:
                        stable_count += 1
                        if stable_count >= 3:
                            break
                    else:
                        stable_count = 0
                    
                    previous_similar_count = len(similar_pins)
                    
                    try:
                        page.wait_for_load_state("networkidle", timeout=3000)
                    except:
                        pass
                
                self.logger.debug(f"Found {len(similar_pins)} similar pins for pin {pin_id}")
                return similar_pins
                
            except Exception as e:
                self.logger.error(f"Error getting similar pins from {pin_id}: {e}")
                return []
            finally:
                browser.close()

    def collect_all_pins(self, keyword, main_count=5, similar_count=None):
        """Collect main pins and optionally their similar pins
        
        Args:
            keyword: Search keyword
            main_count: Number of main pins to collect
            similar_count: Number of similar pins per main pin (None to skip similar pins)
        """
        self.logger.info(f"🚀 Starting pin collection")
        print(f"🚀 Starting Pinterest scraping")
        
        # Step 1: Get main pins
        main_pins = self.get_main_pins_from_search(keyword, main_count)
        
        if not main_pins:
            self.logger.error("No main pins found")
            print("❌ No main pins found")
            return []
        
        all_pin_urls = set(main_pins)  # Start with main pins
        
        # Step 2: Get similar pins if requested
        if similar_count is not None:
            self.logger.info(f"🔍 STEP 2: Getting similar pins from {len(main_pins)} main pins")
            print(f"\n🔍 STEP 2: Getting similar pins from each main pin")
            
            for i, main_pin_url in enumerate(main_pins, 1):
                pin_id = self.extract_pin_id_from_url(main_pin_url)
                self.logger.info(f"Processing main pin {i}/{len(main_pins)}: {pin_id}")
                print(f"   📌 Processing main pin {i}/{len(main_pins)}: {pin_id}")
                
                similar_pins = self.get_similar_pins_from_pin_page(main_pin_url, similar_count)
                
                before_count = len(all_pin_urls)
                all_pin_urls.update(similar_pins)
                after_count = len(all_pin_urls)
                new_pins = after_count - before_count
                
                self.logger.debug(f"Added {new_pins} new similar pins from main pin {pin_id}")
                print(f"      ➕ Added {new_pins} new similar pins ({len(similar_pins)} found, {len(similar_pins)-new_pins} duplicates)")
                
                sleep(1)
            
            self.stats['similar_pins_found'] = len(all_pin_urls) - len(main_pins)
        else:
            self.logger.info("⏭️ Skipping similar pins extraction as per user request")
            print(f"\n⏭️ Skipping similar pins extraction as per user choice")
            self.stats['similar_pins_found'] = 0
        
        self.stats['total_unique_pins'] = len(all_pin_urls)
        
        self.logger.info(f"✅ Total unique pins collected: {len(all_pin_urls)}")
        print(f"\n✅ Collection complete:")
        print(f"   📊 Main pins: {len(main_pins)}")
        print(f"   📊 Similar pins: {self.stats['similar_pins_found']}")
        print(f"   📊 Total unique pins: {len(all_pin_urls)}")
        
        return list(all_pin_urls)

    def get_highest_quality_url(self, image_url):
        """Try 'originals' first, fallback to 1200x"""
        self.logger.debug(f"Getting highest quality URL for: {image_url}")
        
        original_url = image_url.replace("/600x/", "/originals/")
        
        try:
            response = self.session.head(original_url, timeout=10)
            if response.status_code == 200:
                self.logger.debug("Original quality URL available")
                return original_url
            else:
                self.logger.debug(f"Original quality not available (status: {response.status_code}), trying 1200x")
        except Exception as e:
            self.logger.debug(f"Error checking original quality: {e}")
        
        fallback_url = image_url.replace("/600x/", "/1200x/")
        self.logger.debug(f"Using fallback 1200x URL: {fallback_url}")
        return fallback_url

    def extract_image_url(self, pin_url):
        """Extract og:image from the pin page"""
        self.logger.debug(f"Extracting image URL from pin page: {pin_url}")
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.logger.debug("Navigating to pin page")
                page.goto(pin_url, timeout=30000)
                
                self.logger.debug("Waiting for og:image meta tag")
                page.wait_for_selector("meta[property='og:image']", state="attached", timeout=15000)
                
                image_url = page.locator("meta[property='og:image']").get_attribute("content")
                
                if image_url:
                    self.logger.debug(f"Successfully extracted image URL: {image_url}")
                else:
                    self.logger.warning("og:image meta tag found but no content")
                    
            except Exception as e:
                self.logger.error(f"Error extracting image URL: {e}")
                image_url = None
            finally:
                browser.close()
            
            return image_url

    def download_image(self, pin_url):
        """Download image from pin URL"""
        pin_id = self.extract_pin_id_from_url(pin_url)
        if not pin_id:
            self.logger.error(f"❌ Skipped invalid URL: {pin_url}")
            return False

        if self.is_pin_already_processed(pin_id):
            self.stats['skipped_duplicates'] += 1
            return False

        self.logger.info(f"Processing pin: {pin_id}")
        
        image_url = self.extract_image_url(pin_url)
        if not image_url:
            self.logger.error(f"Could not extract image URL for pin {pin_id}")
            self.stats['failed_downloads'] += 1
            return False

        final_url = self.get_highest_quality_url(image_url)
        
        try:
            self.logger.info(f"Downloading image from: {final_url}")
            response = self.session.get(final_url, timeout=30)
            response.raise_for_status()
            
            img_data = response.content
            file_path = os.path.join(self.SAVE_FOLDER, f"{pin_id}.jpg")
            
            with open(file_path, "wb") as f:
                f.write(img_data)
            
            self.mark_pin_as_processed(pin_id)
            
            file_size = len(img_data)
            self.logger.info(f"Successfully downloaded pin {pin_id} - Size: {file_size} bytes")
            self.stats['successful_downloads'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed for pin {pin_id}: {e}")
            self.stats['failed_downloads'] += 1
            return False

    def run(self, keyword, main_count=5, similar_count=None):
        """Main execution method
        
        Args:
            keyword: Search keyword
            main_count: Number of main pins to collect
            similar_count: Number of similar pins per main pin (None to skip similar pins)
        """
        self.logger.info(f"🚀 Starting Pinterest Multi-Level Scraper")
        if similar_count is not None:
            self.logger.info(f"Keyword: '{keyword}', Main pins: {main_count}, Similar per main: {similar_count}")
        else:
            self.logger.info(f"Keyword: '{keyword}', Main pins: {main_count}, Similar pins: Disabled")
        
        start_time = datetime.now()
        
        try:
            # Step 1 & 2: Collect all pins
            all_pin_urls = self.collect_all_pins(keyword, main_count, similar_count)
            
            if not all_pin_urls:
                self.logger.warning("No pins collected")
                print("❌ No pins collected")
                return
            
            # Step 3: Download all collected pins
            self.logger.info(f"🔽 STEP 3: Downloading {len(all_pin_urls)} pins")
            print(f"\n🔽 STEP 3: Downloading {len(all_pin_urls)} pins")
            
            for i, pin_url in enumerate(all_pin_urls, 1):
                pin_id = self.extract_pin_id_from_url(pin_url)
                
                if self.is_pin_already_processed(pin_id):
                    print(f"⏭️  [{i}/{len(all_pin_urls)}] Skipped duplicate: {pin_id}")
                    self.stats['skipped_duplicates'] += 1
                    continue
                
                print(f"📥 [{i}/{len(all_pin_urls)}] Downloading: {pin_id}")
                success = self.download_image(pin_url)
                
                if success:
                    print(f"✅ Downloaded: {pin_id}")
                else:
                    print(f"❌ Failed: {pin_id}")
                
                sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"Critical error in run method: {e}")
            print(f"❌ Critical error: {e}")
        
        # Final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.logger.info("=== MULTI-LEVEL SCRAPING COMPLETED ===")
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"Main pins found: {self.stats['main_pins_found']}")
        self.logger.info(f"Similar pins found: {self.stats['similar_pins_found']}")
        self.logger.info(f"Total unique pins: {self.stats['total_unique_pins']}")
        self.logger.info(f"Successful downloads: {self.stats['successful_downloads']}")
        self.logger.info(f"Skipped duplicates: {self.stats['skipped_duplicates']}")
        self.logger.info(f"Failed downloads: {self.stats['failed_downloads']}")
        self.logger.info(f"Total processed pins in history: {len(self.processed_pins)}")
        
        print(f"\n🎉 Multi-level scraping completed!")
        print(f"⏱️  Duration: {duration}")
        print(f"📊 Main pins: {self.stats['main_pins_found']}")
        print(f"📊 Similar pins: {self.stats['similar_pins_found']}")
        print(f"📊 Total unique pins: {self.stats['total_unique_pins']}")
        print(f"✅ Successful downloads: {self.stats['successful_downloads']}")
        print(f"⏭️  Skipped duplicates: {self.stats['skipped_duplicates']}")
        print(f"❌ Failed downloads: {self.stats['failed_downloads']}")
        print(f"🗂️  Total in history: {len(self.processed_pins)}")

def get_user_input():
    """Get user input for scraping configuration"""
    print("🔥 Pinterest Multi-Level Scraper (Interactive)")
    print("=" * 50)
    
    keyword = input("Enter search keyword: ").strip()
    
    print("\n📋 Configuration:")
    main_count = int(input("How many main pins to collect? (default: 5): ").strip() or "5")
    
    # Ask about similar pins
    print(f"\n✅ Configuration set for {main_count} main pins")
    print("🤔 Do you want to scrape similar pins for each main pin?")
    
    while True:
        user_choice = input("Do we have to scrape similar pins? (Y/N): ").strip().upper()
        if user_choice in ['Y', 'YES']:
            similar_count = int(input("How many similar pins per main pin? (default: 5): ").strip() or "5")
            print(f"   This will search for {similar_count} similar pins per main pin")
            print(f"   Estimated additional pins: {main_count * similar_count}")
            break
        elif user_choice in ['N', 'NO']:
            similar_count = None
            break
        else:
            print("❌ Please enter Y or N")
    
    # Display final configuration
    print(f"\n📊 Final Configuration:")
    print(f"📊 Main pins to collect: {main_count}")
    if similar_count is not None:
        print(f"📊 Similar pins per main pin: {similar_count}")
        print(f"📊 Estimated total pins: {main_count + (main_count * similar_count)}")
    else:
        print(f"📊 Similar pins: Disabled")
        print(f"📊 Total pins: {main_count}")
    print("🔍 Features: Interactive similar pins prompt, 25% page zoom, improved loading")
    
    return keyword, main_count, similar_count

if __name__ == "__main__":
    keyword, main_count, similar_count = get_user_input()
    
    scraper = PinterestScraper()
    scraper.run(keyword, main_count, similar_count)