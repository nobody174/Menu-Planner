import requests
from bs4 import BeautifulSoup

# Test one of the URLs
url = "https://www.hellofresh.no/recipes/mest-populaere-oppskrifter"

print(f"Fetching: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes\n")

    soup = BeautifulSoup(response.content, 'html.parser')

    # Print all script tags (might contain JSON data)
    scripts = soup.find_all('script')
    print(f"Found {len(scripts)} script tags")

    # Look for recipe data in scripts
    for i, script in enumerate(scripts):
        if script.string and 'recipe' in script.string.lower():
            print(f"\nScript {i} contains 'recipe':")
            print(script.string[:500])

    # Look for any links that might be recipe links
    all_links = soup.find_all('a')
    print(f"\n\nFound {len(all_links)} links total")

    # Filter for recipe-like links
    recipe_links = [a for a in all_links if '/recipes/' in a.get('href', '')]
    print(f"Found {len(recipe_links)} recipe links")

    if recipe_links:
        print("\nFirst 5 recipe links:")
        for link in recipe_links[:5]:
            print(f"  {link.get('href')} - {link.text}")

    # Look for divs, articles, or sections that might contain recipes
    print("\n\nLooking for recipe containers...")

    # Try common patterns
    for selector in ['article', 'div[data-testid]', 'div[class*="recipe"]', 'a[href*="/recipes/"]']:
        elements = soup.select(selector)
        if elements:
            print(f"  Found {len(elements)} elements matching '{selector}'")
            if elements and len(elements) < 10:
                for elem in elements[:3]:
                    print(f"    - {elem.get('class')} {elem.get('data-testid')}")

except Exception as e:
    print(f"Error: {e}")
