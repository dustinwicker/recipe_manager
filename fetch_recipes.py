#!/usr/bin/env python3
"""
Fetch recipes from Google Docs and output to data/recipes.json.
Used by GitHub Actions to update the static site.
"""
import json
import os
import sys

# Document IDs (same as app.py)
DOC_ID = '1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY'
QUICK_RECIPE_DOC_ID = '1BpJj3ECDU2Z_QYcorncs3SbeiKUD_WI_Lj29hnRjI18'

def main():
    if not os.environ.get('GOOGLE_SERVICE_ACCOUNT'):
        print('Error: GOOGLE_SERVICE_ACCOUNT environment variable not set')
        sys.exit(1)

    from recipe_parser import RecipeParser

    parser = RecipeParser(DOC_ID, QUICK_RECIPE_DOC_ID, recipe_urls_file='recipe_urls.json')
    recipes = parser.parse()
    recipes = sorted(recipes, key=lambda x: x['title'].lower())

    os.makedirs('data', exist_ok=True)
    with open('data/recipes.json', 'w', encoding='utf-8') as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)

    print(f'Wrote {len(recipes)} recipes to data/recipes.json')

if __name__ == '__main__':
    main()
