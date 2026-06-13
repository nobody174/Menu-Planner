#!/usr/bin/env python
from core.menu_generator import MenuGenerator

print("Testing menu generation with selected categories...")

gen = MenuGenerator(selected_categories=['Familie', 'Rask Middag'])
menu = gen.run(num_dinners=6, save=True)

if menu:
    print(f"SUCCESS: Menu generated with {len(menu.get('dinners', []))} dinners")
    print(f"Selected categories in menu: {menu.get('selected_categories')}")
else:
    print("FAILED: Menu generation returned empty result")
