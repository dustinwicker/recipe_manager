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
                            
                            # Check for links
                            if 'link' in text_run:
                                link = text_run.get('link', {})
                                if 'url' in link:
                                    all_links.append({
                                        'url': link['url'],
                                        'text': content_text.strip()
                                    })
                                    # Use first link as primary
                                    if not link_url:
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
                                'recipe_link': None,
                                'quick_recipe': None,
                                'has_quick_recipe': False,
                                'note': None
                            }
                            current_section = None
                            
                            # Check if this line has a Recipe link
                            if link_url and ('recipe' in line_lower or link_text.lower() == 'recipe'):
                                current_recipe['recipe_link'] = {
                                    'text': link_text if link_text else 'Recipe',
                                    'url': link_url
                                }
                            elif 'recipe' in line_lower:
                                # Check if we have a URL mapping for this recipe
                                if title in self.recipe_urls and self.recipe_urls[title]:
                                    current_recipe['recipe_link'] = {
                                        'text': 'Recipe',
                                        'url': self.recipe_urls[title]
                                    }
                                elif not link_url:
                                    # No link in doc and no mapping - create link to doc
                                    current_recipe['recipe_link'] = {
                                        'text': 'Recipe',
                                        'url': f'https://docs.google.com/document/d/{self.doc_id}/edit'
                                    }
                            
                            # Check if this line mentions Quick_Recipe
                            if 'quick_recipe' in line_lower or 'quick recipe' in line_lower:
                                # Mark that this recipe has a Quick Recipe (even if content is elsewhere)
                                current_recipe['has_quick_recipe'] = True
                                current_section = 'quick_recipe'
                        
                        # Detect standalone "Recipe" text (on its own line)
                        elif current_recipe and line_lower.strip() == 'recipe' and not current_recipe['recipe_link']:
                            if link_url:
                                current_recipe['recipe_link'] = {
                                    'text': 'Recipe',
                                    'url': link_url
                                }
                            elif current_recipe['title'] in self.recipe_urls and self.recipe_urls[current_recipe['title']]:
                                # Use URL from mapping
                                current_recipe['recipe_link'] = {
                                    'text': 'Recipe',
                                    'url': self.recipe_urls[current_recipe['title']]
                                }
                            else:
                                # No link in doc, create a link to the Google Doc itself
                                current_recipe['recipe_link'] = {
                                    'text': 'Recipe',
                                    'url': f'https://docs.google.com/document/d/{self.doc_id}/edit'
                                }
                        
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
                        elif current_recipe:
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
        if not current_recipe or (current_recipe and (current_recipe.get('recipe_link') or current_recipe.get('quick_recipe') or current_recipe.get('note'))):
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
        if recipe.get('recipe_link'):
            print(f"   Recipe Link: {recipe['recipe_link']['text']} -> {recipe['recipe_link']['url']}")
        if recipe.get('quick_recipe'):
            print(f"   Quick Recipe: {recipe['quick_recipe'][:60]}...")
        if recipe.get('note'):
            print(f"   Note: {recipe['note'][:60]}...")
        print()

