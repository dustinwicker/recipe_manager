#!/usr/bin/env python3
"""
Parse Quick Recipe document to extract quick recipe information.
"""

import creds
from googleapiclient.discovery import build
import re
from typing import Dict, List


class QuickRecipeParser:
    """Parse quick recipes from Google Docs."""
    
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.quick_recipes = {}  # title -> quick_recipe_text
    
    def parse(self) -> Dict[str, str]:
        """Parse the document and return dict of recipe title -> quick recipe text."""
        credentials = creds.login()
        service = build('docs', 'v1', credentials=credentials)
        
        try:
            doc = service.documents().get(documentId=self.doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            current_recipe_title = None
            quick_recipe_lines = []
            
            for element in content:
                if 'paragraph' in element:
                    para = element.get('paragraph', {})
                    elements = para.get('elements', [])
                    paragraph_text = ''
                    
                    for elem in elements:
                        if 'textRun' in elem:
                            text_run = elem.get('textRun', {})
                            content_text = text_run.get('content', '')
                            text_style = text_run.get('textStyle', {})
                            
                            if not text_style.get('strikethrough', False):
                                paragraph_text += content_text
                    
                    if paragraph_text.strip():
                        line = paragraph_text.strip()
                        line_lower = line.lower()
                        
                        # Preserve bullet/indent formatting
                        bullet = para.get('bullet')
                        if bullet is not None:
                            nesting = bullet.get('nestingLevel', 0)
                            indent = '  ' * nesting
                            line = f'{indent}- {line}'
                        
                        # Detect recipe title (similar to main parser)
                        if self._is_recipe_title(line) and not bullet:
                            # Save previous recipe
                            if current_recipe_title and quick_recipe_lines:
                                self.quick_recipes[current_recipe_title] = '\n'.join(quick_recipe_lines)
                            
                            # Extract recipe title (strip bullet prefix if we added it)
                            title = paragraph_text.strip()
                            # Remove common suffixes
                            for suffix in [' recipe', ' quick_recipe', ' quick recipe']:
                                if suffix in line_lower:
                                    title = title[:line_lower.index(suffix)].strip()
                                    break
                            
                            current_recipe_title = title
                            quick_recipe_lines = []
                        elif current_recipe_title:
                            # This is content for the current recipe
                            quick_recipe_lines.append(line)
            
            # Save last recipe
            if current_recipe_title and quick_recipe_lines:
                self.quick_recipes[current_recipe_title] = '\n'.join(quick_recipe_lines)
            
            return self.quick_recipes
        
        except Exception as e:
            # Silently fail - document might not be shared yet
            # Error will be: HttpError 403 - permission denied
            return {}
    
    def _is_recipe_title(self, line: str) -> bool:
        """Determine if a line is a recipe title."""
        line_lower = line.lower()
        
        # Pattern: Recipe name followed by "Recipe" or "Quick_Recipe"
        if ' recipe' in line_lower or ' quick_recipe' in line_lower or ' quick recipe' in line_lower:
            if line_lower.strip() not in ['recipe', 'quick_recipe', 'quick recipe']:
                return True
        
        # Not a title if it's clearly content
        if any(keyword in line_lower for keyword in ['oven:', 'degrees', 'deg', 'min', 'minutes']):
            return False
        
        # Not a title if it starts with a number
        if re.match(r'^\d+', line):
            return False
        
        # Short lines that aren't instructions might be titles
        if len(line) < 60:
            return True
        
        return False


if __name__ == "__main__":
    # Test parsing
    parser = QuickRecipeParser('1BpJj3ECDU2Z_QYcorncs3SbeiKUD_WI_Lj29hnRjI18')
    quick_recipes = parser.parse()
    
    print(f"\nFound {len(quick_recipes)} quick recipes:\n")
    for title, content in list(quick_recipes.items())[:10]:
        print(f"{title}:")
        print(f"  {content[:80]}...")
        print()

