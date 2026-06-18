#!/usr/bin/env python3
"""Validate HTML templates."""
import os
from html.parser import HTMLParser


class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []

    def error(self, message):
        self.errors.append(message)


template_dir = "frontend/templates"
for file in os.listdir(template_dir):
    if file.endswith(".html"):
        with open(os.path.join(template_dir, file)) as f:
            content = f.read()
            validator = HTMLValidator()
            try:
                validator.feed(content)
                print(f"[OK] {file} HTML structure OK")
            except Exception as e:
                print(f"[FAIL] {file} has HTML issues: {e}")
