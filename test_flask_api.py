#!/usr/bin/env python
import sys
from pathlib import Path
import os

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'pi-deployment'))

from flask_app import app

print("Testing Flask API endpoints...")

with app.test_client() as client:
    # Test /api/categories endpoint
    print("\n1. Testing GET /api/categories")
    response = client.get('/api/categories')
    print(f"   Status: {response.status_code}")
    data = response.get_json()
    categories = data.get('categories', [])
    print(f"   Categories available: {len(categories)}")
    print(f"   Sample: {categories[:3]}")

    # Test /api/regenerate endpoint with selected categories
    print("\n2. Testing POST /api/regenerate with selected categories")
    response = client.post(
        '/api/regenerate',
        json={'selected_categories': ['Familie', 'Rask Middag']},
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    data = response.get_json()
    if data.get('status') == 'success':
        menu = data.get('menu', {})
        print(f"   Menu generated successfully")
        print(f"   Dinners: {len(menu.get('dinners', []))}")
        print(f"   Selected categories in response: {menu.get('selected_categories')}")
    else:
        print(f"   Error: {data.get('message')}")

print("\n3. Testing /api/categories with default categories")
response = client.post(
    '/api/regenerate',
    json={},  # Empty body, should use defaults
    content_type='application/json'
)
print(f"   Status: {response.status_code}")
data = response.get_json()
if data.get('status') == 'success':
    menu = data.get('menu', {})
    print(f"   Default categories used: {menu.get('selected_categories')}")
else:
    print(f"   Error: {data.get('message')}")

print("\nAll API tests completed!")
