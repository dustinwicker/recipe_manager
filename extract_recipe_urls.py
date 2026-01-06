#!/usr/bin/env python3
"""
Extract recipe URLs from the Google Doc and update recipe_urls.json.
This script looks for hyperlinks on the word "Recipe" and associates them with recipe titles.
"""

import creds
from googleapiclient.discovery import build
import json
import re
import os

def extract_recipe_urls(doc_id, recipe_urls_file='recipe_urls.json'):
    """Extract all recipe URLs from the document."""
    credentials = creds.login()
    service = build('docs', 'v1', credentials=credentials)
    
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        content = doc.get('body', {}).get('content', [])
        
        recipes_with_urls = {}
        current_recipe_title = None
        pending_url = None  # URL found but not yet associated with a recipe
        
        for element in content:
            if 'paragraph' in element:
                para = element.get('paragraph', {})
                elements = para.get('elements', [])
                paragraph_text = ''
                found_recipe_link = None
                
                # First pass: collect text and find recipe title
                for elem in elements:
                    if 'textRun' in elem:
                        text_run = elem.get('textRun', {})
                        content_text = text_run.get('content', '')
                        paragraph_text += content_text
                
                line = paragraph_text.strip()
                line_lower = line.lower()
                
                # Second pass: look for links and recipe titles
                for elem in elements:
                    if 'textRun' in elem:
                        text_run = elem.get('textRun', {})
                        content_text = text_run.get('content', '').strip()
                        
                        # Check for links
                        if 'link' in text_run:
                            link = text_run.get('link', {})
                            if 'url' in link:
                                url = link['url']
                                # Skip Google Doc URLs
                                if 'docs.google.com' not in url:
                                    # If this link is on "Recipe" text, save it
                                    if 'recipe' in content_text.lower():
                                        found_recipe_link = url
                
                # Detect recipe title
                if ' recipe' in line_lower or ' quick_recipe' in line_lower:
                    if line_lower.strip() not in ['recipe', 'quick_recipe', 'quick recipe']:
                        # Extract recipe title
                        title = line
                        if ' recipe' in line_lower:
                            title = line[:line_lower.index(' recipe')].strip()
                        elif ' quick_recipe' in line_lower:
                            title = line[:line_lower.index(' quick_recipe')].strip()
                        elif ' quick recipe' in line_lower:
                            title = line[:line_lower.index(' quick recipe')].strip()
                        
                        current_recipe_title = title
                        
                        # If we found a recipe link in this same paragraph, associate it
                        if found_recipe_link:
                            recipes_with_urls[title] = found_recipe_link
                            print(f"Found: {title} -> {found_recipe_link}")
                            pending_url = None
                
                # Check for standalone "Recipe" line
                elif current_recipe_title and line_lower.strip() == 'recipe':
                    if found_recipe_link:
                        recipes_with_urls[current_recipe_title] = found_recipe_link
                        print(f"Found: {current_recipe_title} -> {found_recipe_link}")
                        pending_url = None
                    elif pending_url and current_recipe_title not in recipes_with_urls:
                        # Use pending URL from previous paragraph
                        recipes_with_urls[current_recipe_title] = pending_url
                        print(f"Found (pending): {current_recipe_title} -> {pending_url}")
                        pending_url = None
                
                # If we found a URL but no recipe title yet, save it as pending
                elif found_recipe_link and not current_recipe_title:
                    pending_url = found_recipe_link
        
        # Load existing recipe_urls.json
        if os.path.exists(recipe_urls_file):
            with open(recipe_urls_file, 'r') as f:
                all_recipes = json.load(f)
        else:
            all_recipes = {}
        
        # Update with found URLs (only if they don't already exist or are empty)
        updated_count = 0
        for title, url in recipes_with_urls.items():
            if title in all_recipes:
                if not all_recipes[title] or all_recipes[title] == "":
                    all_recipes[title] = url
                    updated_count += 1
            else:
                all_recipes[title] = url
                updated_count += 1
        
        # Write back
        with open(recipe_urls_file, 'w') as f:
            json.dump(all_recipes, f, indent=2)
        
        print(f"\nUpdated {updated_count} recipes in {recipe_urls_file}")
        print(f"Total recipes with URLs: {sum(1 for v in all_recipes.values() if v)}")
        
        return recipes_with_urls
        
    except Exception as e:
        print(f"Error extracting URLs: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == '__main__':
    doc_id = '1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY'
    extract_recipe_urls(doc_id)

