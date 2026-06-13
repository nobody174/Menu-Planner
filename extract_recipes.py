import requests
import json
import re
from bs4 import BeautifulSoup

url = "https://www.hellofresh.no/recipes/mest-populaere-oppskrifter"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(response.content, 'html.parser')

# Find script tags that might contain JSON
scripts = soup.find_all('script')

for i, script in enumerate(scripts):
    if not script.string:
        continue

    content = script.string

    # Look for JSON that contains recipe data
    if 'recipesPage' in content or 'recipes' in content:
        print(f"\n=== Script {i} ===")

        # Try to extract JSON
        try:
            # Find JSON objects
            if content.startswith('{'):
                # Parse the entire script content as JSON
                data = json.loads(content)
                print(json.dumps(data, indent=2)[:1000])
        except:
            # Try to find recipe data in the string
            if 'title' in content and 'recipe' in content.lower():
                # Find patterns like "title":"..."
                titles = re.findall(r'"title":"([^"]+)"', content)
                if titles:
                    print(f"Found {len(titles)} potential titles:")
                    for title in titles[:10]:
                        print(f"  - {title}")
