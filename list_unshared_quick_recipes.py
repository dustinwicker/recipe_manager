#!/usr/bin/env python3
"""
List Quick Recipe Google Docs that are not shared with the service account.
These recipes have Quick Recipe links but no content was fetched (quick_recipe is null).
"""
import json
import re
import sys

def extract_doc_id(url):
    match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

def is_quick_recipe_link(link_text):
    if not link_text:
        return False
    lt = link_text.lower()
    return 'quick_recipe' in lt or 'quick recipe' in lt or lt.rstrip().endswith('_recipe')

def main():
    with open('data/recipes.json', 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    unshared = []
    seen_urls = set()

    for r in recipes:
        if r.get('quick_recipe'):
            continue  # Has content, skip
        for link in r.get('google_doc_links', []):
            url = link.get('url', '')
            if 'docs.google.com' not in url:
                continue
            if not is_quick_recipe_link(link.get('text', '')):
                continue
            doc_id = extract_doc_id(url)
            if doc_id and url not in seen_urls:
                seen_urls.add(url)
                unshared.append({
                    'recipe': r['title'],
                    'link_text': link.get('text', ''),
                    'url': url,
                })

    if not unshared:
        print('All Quick Recipe Google Docs appear to be shared.')
        return

    print(f'Quick Recipe Google Docs to share with your service account ({len(unshared)}):\n')
    print('Share each document with: self-550@creds-443417.iam.gserviceaccount.com\n')
    print('-' * 80)
    for i, item in enumerate(unshared, 1):
        print(f"{i}. {item['recipe']}")
        print(f"   Link: {item['link_text']}")
        print(f"   URL:  {item['url']}")
        print()

if __name__ == '__main__':
    main()
