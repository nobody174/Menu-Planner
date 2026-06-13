import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://www.hellofresh.no/recipes/mest-populaere-oppskrifter"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("Checking for pagination/load-more elements...")

        # Look for common pagination patterns
        patterns = [
            'button:has-text("Load more")',
            'button:has-text("Vis mer")',
            'button:has-text("Next")',
            'a[rel="next"]',
            'div[class*="pagination"]',
            'nav[aria-label*="paginat"]',
        ]

        for selector in patterns:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"  Found: {selector} - {len(elements)} elements")

        # Check page height and scroll
        print(f"\nChecking scroll behavior...")
        initial_height = await page.evaluate("document.body.scrollHeight")
        print(f"  Initial page height: {initial_height}px")

        # Try scrolling to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

        new_height = await page.evaluate("document.body.scrollHeight")
        print(f"  Height after scroll: {new_height}px")

        if new_height > initial_height:
            print("  [YES] Page has infinite scroll - more content loaded on scroll!")
        else:
            print("  [NO] No infinite scroll detected")

        # Count recipe elements at different scroll points
        text_before = await page.inner_text('body')
        recipes_before = text_before.count('minutter')
        print(f"\n  Recipes visible before scroll: ~{recipes_before}")

        await browser.close()

asyncio.run(check())
