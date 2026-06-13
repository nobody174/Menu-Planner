import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://www.hellofresh.no/recipes/mest-populaere-oppskrifter"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)  # Wait 3 seconds for JavaScript to render

        # Get the page HTML
        html = await page.content()

        # Print first 3000 chars
        print("First 3000 chars of page HTML:")
        print(html[:3000])

        print("\n\n=== Looking for links ===")

        # Get all links
        links = await page.query_selector_all('a')
        print(f"Total links on page: {len(links)}")

        print("\nFirst 10 links:")
        for i, link in enumerate(links[:10]):
            href = await link.get_attribute('href')
            text = await link.inner_text()
            print(f"  {i+1}. href={href}, text={text[:50]}")

        # Look for specific text patterns
        print("\n=== Looking for recipe-like content ===")
        all_text = await page.inner_text('body')
        lines = all_text.split('\n')
        recipe_lines = [l for l in lines if len(l) > 5 and len(l) < 100]
        print(f"Found {len(recipe_lines)} potential recipe title lines")
        print("First 20:")
        for line in recipe_lines[:20]:
            print(f"  - {line}")

        await browser.close()

asyncio.run(debug())
