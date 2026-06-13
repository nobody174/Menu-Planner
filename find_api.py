import requests
import json

# Hello Fresh likely uses an API to fetch recipes
# Common patterns: /api/recipes, /graphql, etc.

# Try some common API endpoints
base_url = "https://www.hellofresh.no"

# Try REST API patterns
endpoints = [
    "/api/recipes/mest-populaere-oppskrifter",
    "/api/recipes?category=mest-populaere-oppskrifter",
    "/api/recipes",
    "/graphql",  # Try GraphQL
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for endpoint in endpoints:
    url = base_url + endpoint
    print(f"\nTrying: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Valid JSON! Keys: {list(data.keys())[:10]}")

                # Check if it contains recipes
                if isinstance(data, dict):
                    for key in ['recipes', 'data', 'results', 'items']:
                        if key in data:
                            items = data[key]
                            if isinstance(items, list) and items:
                                print(f"  Found {len(items)} items in '{key}'")
                                if len(items) > 0:
                                    print(f"    First item: {json.dumps(items[0], indent=2)[:200]}")
            except:
                print(f"  Not JSON or too large")
    except Exception as e:
        print(f"  Error: {e}")
