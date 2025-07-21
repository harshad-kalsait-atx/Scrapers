# In this code snippet, 
# we will scrape a Scribd document and save it as a PDF using Playwright in Python.
# The code will navigate to the Scribd document, wait for it to load, and then print it as a PDF.
#Manual waiting is used to ensure the document is fully loaded before printing.

import asyncio
from playwright.async_api import async_playwright

SCRIBD_DOC_URL = "https://www.scribd.com/embeds/718275947/content"
SCRIBD_PRESENTATION_URL = "https://www.scribd.com/embeds/513168371/content"

async def scrape_and_print_scribd():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # set headless=True for silent run
        page = await browser.new_page()
        await page.goto(SCRIBD_PRESENTATION_URL, wait_until='networkidle')

        # Wait for the document to load fully
        await page.wait_for_selector('div.outer_page_container', timeout=60000)

        # Move the target div into body and remove all other elements
        await page.evaluate("""
            () => {
                const outerDiv = document.querySelector('div.outer_page_container');
                document.body.innerHTML = '';  // Clear everything in body
                document.body.appendChild(outerDiv);  // Add only the desired div
                document.body.style.margin = '0';
            }
        """)

        # Optional: Wait for manual view before printing
        print("Ready to print. Press Enter to continue...")
        input()

        # Save as PDF using browser context
        pdf_path = 'scribd_document_multiple.pdf'
        await page.pdf(path=pdf_path, format="A4", print_background=True)
        print(f"PDF saved to {pdf_path}")

        await browser.close()

asyncio.run(scrape_and_print_scribd())

