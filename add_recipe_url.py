#!/usr/bin/env python3
"""
Helper script to add recipe URLs to recipe_urls.json.
Usage: python3 add_recipe_url.py "Recipe Title" "https://example.com/recipe"
"""

import json
import sys
import os

def add_recipe_url(title, url, recipe_urls_file='recipe_urls.json'):
    """Add or update a recipe URL."""
    # Load existing URLs
    if os.path.exists(recipe_urls_file):
        with open(recipe_urls_file, 'r') as f:
            recipes = json.load(f)
    else:
        recipes = {}
    
    # Update or add the URL
    recipes[title] = url
    
    # Write back
    with open(recipe_urls_file, 'w') as f:
        json.dump(recipes, f, indent=2)
    
    print(f"Added/Updated: {title} -> {url}")
    return recipes

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 add_recipe_url.py \"Recipe Title\" \"https://example.com/recipe\"")
        sys.exit(1)
    
    title = sys.argv[1]
    url = sys.argv[2]
    add_recipe_url(title, url)

