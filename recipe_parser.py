#!/usr/bin/env python3
"""
Parse Google Docs recipe document and extract recipe information.
"""

import creds
from googleapiclient.discovery import build
import re
import json
import os
from typing import Dict, List, Optional


class RecipeParser:
    """Parse recipes from Google Docs."""
    
    def __init__(self, doc_id: str, quick_recipe_doc_id: str = None, recipe_urls_file: str = None):
        self.doc_id = doc_id
        self.quick_recipe_doc_id = quick_recipe_doc_id
        self.recipe_urls_file = recipe_urls_file or 'recipe_urls.json'
        self.recipes = []
        self.recipe_urls = self._load_recipe_urls()
    
    def _load_recipe_urls(self) -> Dict[str, str]:
        """Load recipe URLs from JSON file if it exists."""
        if os.path.exists(self.recipe_urls_file):
            try:
                with open(self.recipe_urls_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def parse(self) -> List[Dict]:
        """Parse the document and return list of recipes."""
        credentials = creds.login()
        service = build('docs', 'v1', credentials=credentials)
        
        try:
            doc = service.documents().get(documentId=self.doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            current_recipe = None
            current_section = None  # 'recipe', 'quick_recipe', 'note'
            
            for element in content:
                if 'paragraph' in element:
                    para = element.get('paragraph', {})
                    elements = para.get('elements', [])
                    paragraph_text = ''
                    link_url = None
                    link_text = ''
                    
                    # Extract text and links
                    all_links = []  # Collect all links in this paragraph
                    for elem in elements:
                        if 'textRun' in elem:
                            text_run = elem.get('textRun', {})
                            content_text = text_run.get('content', '')
                            text_style = text_run.get('textStyle', {})
                            
                            # Check for links - they can be in textRun.link OR textStyle.link
                            link = None
                            if 'link' in text_run:
                                link = text_run.get('link', {})
                            elif 'textStyle' in text_run:
                                text_style = text_run.get('textStyle', {})
                                if 'link' in text_style:
                                    link = text_style.get('link', {})
                            
                            if link and 'url' in link:
                                link_info = {
                                    'url': link['url'],
                                    'text': content_text.strip()
                                }
                                all_links.append(link_info)
                                # Use first link as primary, but prefer "Recipe" links
                                if not link_url:
                                    link_url = link['url']
                                    link_text = content_text.strip()
                                # If we find a link on text containing "recipe", use that instead
                                elif 'recipe' in content_text.lower() and 'docs.google.com' not in link['url']:
                                    link_url = link['url']
                                    link_text = content_text.strip()
                            
                            if not text_style.get('strikethrough', False):
                                paragraph_text += content_text
                    
                    # Also check for URLs in the text itself (not just hyperlinks)
                    url_pattern = re.compile(r'https?://[^\s\)]+')
                    urls_in_text = url_pattern.findall(paragraph_text)
                    if urls_in_text and not link_url:
                        # Use first URL found in text
                        link_url = urls_in_text[0]
                        link_text = 'Recipe'
                    
                    if paragraph_text.strip():
                        line = paragraph_text.strip()
                        line_lower = line.lower()
                        
                        # Detect recipe title - look for lines that are recipe names
                        # Pattern: Recipe name followed by "Recipe" or "Quick_Recipe" or just standalone
                        if self._is_recipe_title(line, current_recipe):
                            # Save previous recipe
                            if current_recipe:
                                self.recipes.append(current_recipe)
                            
                            # Extract recipe title (remove "Recipe", "Quick_Recipe" suffixes)
                            title = line
                            if ' recipe' in line_lower:
                                title = line[:line_lower.index(' recipe')].strip()
                            elif ' quick_recipe' in line_lower or ' quick recipe' in line_lower:
                                title = line[:line_lower.index(' quick')].strip()
                            
                            # Start new recipe
                            current_recipe = {
                                'title': title,
                                'external_links': [],  # External URLs (non-Google Doc)
                                'google_doc_links': [],  # Google Doc URLs
                                'quick_recipe': None,
                                'has_quick_recipe': False,
                                'note': None
                            }
                            current_section = None
                            
                            # Collect ALL links from this paragraph
                            # Priority: 1) recipe_urls.json mapping, 2) links in document
                            if 'recipe' in line_lower:
                                # First, check if we have URLs in recipe_urls.json (highest priority)
                                # Note: recipe_urls.json currently only supports single URL per recipe
                                # Document links will be added separately and take precedence for multiple links
                                if title in self.recipe_urls and self.recipe_urls[title]:
                                    url = self.recipe_urls[title]
                                    if url:  # Only add if URL is not empty
                                        # Only add from recipe_urls.json if we don't have document links
                                        # This allows document links to override recipe_urls.json
                                        pass  # Skip recipe_urls.json when we have document links
                                
                                # Second, collect all links from the document (avoid duplicates)
                                for link_info in all_links:
                                    url = link_info['url']
                                    link_text = link_info['text'] or 'Recipe'
                                    
                                    if 'docs.google.com' in url:
                                        # Google Doc link - check for duplicates
                                        if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                            current_recipe['google_doc_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    else:
                                        # External link - check for duplicates
                                        if not any(l['url'] == url for l in current_recipe['external_links']):
                                            current_recipe['external_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                
                                # If no links found at all, add default Google Doc link
                                if not current_recipe['external_links'] and not current_recipe['google_doc_links']:
                                    current_recipe['google_doc_links'].append({
                                        'text': 'Recipe',
                                        'url': f'https://docs.google.com/document/d/{self.doc_id}/edit'
                                    })
                            
                            # Check if this line mentions Quick_Recipe
                            if 'quick_recipe' in line_lower or 'quick recipe' in line_lower:
                                # Mark that this recipe has a Quick Recipe (even if content is elsewhere)
                                current_recipe['has_quick_recipe'] = True
                                current_section = 'quick_recipe'
                        
                        # Detect standalone "Recipe" text (on its own line)
                        elif current_recipe and line_lower.strip() == 'recipe':
                            # Collect all links from this paragraph
                            for link_info in all_links:
                                url = link_info['url']
                                link_text = link_info['text'] or 'Recipe'
                                
                                if 'docs.google.com' in url:
                                    # Avoid duplicates
                                    if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                        current_recipe['google_doc_links'].append({
                                            'text': link_text,
                                            'url': url
                                        })
                                else:
                                    # Avoid duplicates
                                    if not any(l['url'] == url for l in current_recipe['external_links']):
                                        current_recipe['external_links'].append({
                                            'text': link_text,
                                            'url': url
                                        })
                            
                            # If still no links, check recipe_urls.json or add default
                            if not current_recipe['external_links'] and not current_recipe['google_doc_links']:
                                title = current_recipe['title']
                                if title in self.recipe_urls and self.recipe_urls[title]:
                                    url = self.recipe_urls[title]
                                    if 'docs.google.com' in url:
                                        current_recipe['google_doc_links'].append({
                                            'text': 'Recipe',
                                            'url': url
                                        })
                                    else:
                                        current_recipe['external_links'].append({
                                            'text': 'Recipe',
                                            'url': url
                                        })
                                else:
                                    # Default to Google Doc
                                    current_recipe['google_doc_links'].append({
                                        'text': 'Recipe',
                                        'url': f'https://docs.google.com/document/d/{self.doc_id}/edit'
                                    })
                        
                        # Detect "Quick Recipe" section (standalone line or content)
                        elif current_recipe and ('quick_recipe' in line_lower or 'quick recipe' in line_lower):
                            current_section = 'quick_recipe'
                            current_recipe['has_quick_recipe'] = True
                            # If this line has actual content (not just "Quick_Recipe"), capture it
                            if line_lower not in ['quick_recipe', 'quick recipe']:
                                if current_recipe['quick_recipe']:
                                    current_recipe['quick_recipe'] += '\n' + line
                                else:
                                    current_recipe['quick_recipe'] = line
                        
                        # Detect "Note" section
                        elif current_recipe and line_lower.startswith('note'):
                            current_section = 'note'
                            # Extract note text (remove "Note:" or "Note " prefix)
                            note_text = re.sub(r'^note:?\s*', '', line, flags=re.I)
                            current_recipe['note'] = note_text
                        
                        # Add content to current section
                        # Also collect any links from paragraphs after recipe title (but before next recipe)
                        elif current_recipe:
                            # Only collect links if we haven't started a new section (note/quick_recipe)
                            # and the line doesn't look like a new recipe title
                            is_likely_new_recipe = (
                                len(line) < 80 and 
                                not any(kw in line_lower for kw in ['note:', 'note ', 'quick_recipe', 'quick recipe']) and
                                not re.match(r'^\d+[\.\)]', line) and
                                not any(line_lower.startswith(kw) for kw in ['preheat', 'cook', 'bake', 'fry', 'boil', 'mix'])
                            )
                            
                            # Collect links from this paragraph (but only if it's not a new recipe)
                            # Links should be collected early, before we get into note/quick_recipe sections
                            if not current_section or current_section not in ['note', 'quick_recipe']:
                                for link_info in all_links:
                                    url = link_info['url']
                                    link_text = link_info['text'] or 'Recipe'
                                    
                                    if 'docs.google.com' in url:
                                        # Avoid duplicates
                                        if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                            current_recipe['google_doc_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    else:
                                        # Avoid duplicates
                                        if not any(l['url'] == url for l in current_recipe['external_links']):
                                            current_recipe['external_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                            
                            if current_section == 'quick_recipe':
                                if current_recipe['quick_recipe']:
                                    current_recipe['quick_recipe'] += '\n' + line
                                else:
                                    current_recipe['quick_recipe'] = line
                            elif current_section == 'note':
                                if current_recipe['note']:
                                    current_recipe['note'] += '\n' + line
                                else:
                                    current_recipe['note'] = line
            
            # Add last recipe
            if current_recipe:
                self.recipes.append(current_recipe)
            
            # Load quick recipes if doc ID provided
            if self.quick_recipe_doc_id:
                try:
                    from quick_recipe_parser import QuickRecipeParser
                    quick_parser = QuickRecipeParser(self.quick_recipe_doc_id)
                    quick_recipes = quick_parser.parse()
                    
                    # Match quick recipes to main recipes by title
                    for recipe in self.recipes:
                        title = recipe['title']
                        # Try exact match first
                        if title in quick_recipes:
                            recipe['quick_recipe'] = quick_recipes[title]
                            recipe['has_quick_recipe'] = True
                        else:
                            # Try case-insensitive match
                            for quick_title, quick_content in quick_recipes.items():
                                if title.lower() == quick_title.lower():
                                    recipe['quick_recipe'] = quick_content
                                    recipe['has_quick_recipe'] = True
                                    break
                except Exception as e:
                    # Silently fail - document might not be shared yet
                    pass
            
            return self.recipes
        
        except Exception as e:
            print(f"Error parsing document: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_recipe_title(self, line: str, current_recipe: Optional[Dict]) -> bool:
        """Determine if a line is a recipe title."""
        line_lower = line.lower()
        
        # Pattern: Recipe name followed by "Recipe" or "Quick_Recipe"
        # Examples: "Chicken Breast Recipe", "Salmon Quick_Recipe", "Tilapia Quick_Recipe"
        if ' recipe' in line_lower or ' quick_recipe' in line_lower or ' quick recipe' in line_lower:
            # Make sure it's not just "Recipe" or "Quick Recipe" alone
            if line_lower.strip() not in ['recipe', 'quick_recipe', 'quick recipe']:
                return True
        
        # Also check for standalone recipe names (without Recipe suffix)
        # But only if we don't have a current recipe or current recipe is complete
        if not current_recipe or (current_recipe and (current_recipe.get('external_links') or current_recipe.get('google_doc_links') or current_recipe.get('quick_recipe') or current_recipe.get('note'))):
            # Not a title if it's clearly a section header
            if any(keyword in line_lower for keyword in ['note:', 'note ']):
                return False
            
            # Not a title if it starts with common instruction words
            if any(line_lower.startswith(kw) for kw in ['preheat', 'cook', 'bake', 'fry', 'boil', 'mix']):
                return False
            
            # Not a title if it's a numbered step
            if re.match(r'^\d+[\.\)]', line):
                return False
            
            # Likely a title if it's a short line (under 80 chars) and not obviously an instruction
            if len(line) < 80 and not any(kw in line_lower for kw in ['degrees', 'minutes', 'hours', 'cup', 'tbsp', 'tsp', 'preheat', 'cook', 'bake']):
                return True
        
        return False


if __name__ == "__main__":
    # Test parsing
    parser = RecipeParser('1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY')
    recipes = parser.parse()
    
    print(f"\nFound {len(recipes)} recipes:\n")
    for i, recipe in enumerate(recipes, 1):
        print(f"{i}. {recipe['title']}")
        if recipe.get('external_links'):
            for link in recipe['external_links']:
                print(f"   External Link: {link['text']} -> {link['url']}")
        if recipe.get('google_doc_links'):
            for link in recipe['google_doc_links']:
                print(f"   Google Doc Link: {link['text']} -> {link['url']}")
        if recipe.get('quick_recipe'):
            print(f"   Quick Recipe: {recipe['quick_recipe'][:60]}...")
        if recipe.get('note'):
            print(f"   Note: {recipe['note'][:60]}...")
        print()

