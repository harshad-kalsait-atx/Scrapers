# pinterest_scraper.py

import asyncio
import aiohttp
import os
import re
from playwright.async_api import async_playwright
from urllib.parse import quote

class PinterestScraper:
    def __init__(self):
        self.SAVE_FOLDER = "scraped_data/pinterest_images"
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)
        self.downloaded_files = set()

    async def download_image(self, session, url, index, query):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.pinterest.com'
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    ext = 'jpg'
                    if 'png' in content_type:
                        ext = 'png'
                    elif 'webp' in content_type:
                        ext = 'webp'

                    filename = f"{query.replace(' ', '_')}_{index}.{ext}"
                    filepath = os.path.join(self.SAVE_FOLDER, filename)

                    if os.path.exists(filepath) or filename in self.downloaded_files:
                        print(f"Skipped: {filename}")
                        return False

                    with open(filepath, 'wb') as f:
                        f.write(await response.read())

                    self.downloaded_files.add(filename)
                    print(f"Downloaded: {filename}")
                    return True
                else:
                    print(f"Failed (status {response.status}): {url}")
                    return False
        except Exception as e:
            print(f"Error downloading image {index}: {e}")
            return False

    async def get_pinterest_images(self, query, max_images=10):
        query_encoded = quote(query)
        url = f"https://www.pinterest.com/search/pins/?q={query_encoded}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                for _ in range(5):
                    await page.mouse.wheel(0, 5000)
                    await page.wait_for_timeout(2000)

                html = await page.content()
                image_urls = list(set(re.findall(r'https://i\.pinimg\.com/[^"]+\.(?:jpg|png|webp)', html)))

                print(f"Found {len(image_urls)} image URLs on Pinterest.")
                return image_urls[:max_images]

            except Exception as e:
                print(f"Error scraping Pinterest: {e}")
                return []

            finally:
                await browser.close()

    async def run(self, query, max_images=10):
        print(f"[PinterestScraper] Query: '{query}', max: {max_images}")
        image_urls = await self.get_pinterest_images(query, max_images)

        if not image_urls:
            print("No images found.")
            return

        connector = aiohttp.TCPConnector(limit=5)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for idx, url in enumerate(image_urls):
                tasks.append(self.download_image(session, url, idx, query))
                if len(tasks) >= 5 or idx == len(image_urls) - 1:
                    await asyncio.gather(*tasks)
                    tasks = []
                    await asyncio.sleep(1)

if __name__ == "__main__":
    async def main():
        scraper = PinterestScraper()
        await scraper.run("Mexico documentos", max_images=10)

    asyncio.run(main())
