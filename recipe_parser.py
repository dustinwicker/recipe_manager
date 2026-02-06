#!/usr/bin/env python3
"""
Parse Google Docs recipe document and extract recipe information.
"""

import creds
from googleapiclient.discovery import build
import re
import json
import os
from typing import Dict, List, Optional, Tuple


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
                            
                            # Extract recipe title - only use text BEFORE the first hyperlink
                            # This ensures we only get the recipe name, not additional text like "Tyler Tolman"
                            title_parts = []
                            for elem in elements:
                                if 'textRun' in elem:
                                    text_run = elem.get('textRun', {})
                                    content_text = text_run.get('content', '').strip()
                                    
                                    # Check if this text is a link
                                    is_link = False
                                    if 'link' in text_run:
                                        is_link = True
                                    elif 'textStyle' in text_run:
                                        text_style = text_run.get('textStyle', {})
                                        if 'link' in text_style:
                                            is_link = True
                                    
                                    # Stop collecting title text when we hit the first link
                                    if is_link:
                                        break
                                    
                                    # Only add non-empty text that's not a link
                                    if content_text:
                                        title_parts.append(content_text)
                            
                            # Join the title parts
                            title = ' '.join(title_parts).strip()
                            
                            # Remove "Recipe", "Quick_Recipe" suffixes if present
                            title_lower = title.lower()
                            if ' recipe' in title_lower:
                                title = title[:title_lower.index(' recipe')].strip()
                            elif ' quick_recipe' in title_lower or ' quick recipe' in title_lower:
                                title = title[:title_lower.index(' quick')].strip()
                            
                            # Remove _Recipe and _Picture suffixes from title
                            # These appear as separate words like "Trevor_Recipe" or "Mom_Recipe"
                            # Remove any word that matches _Something_Recipe or _Something_Picture pattern
                            words = title.split()
                            cleaned_words = []
                            for word in words:
                                # Skip words that match _Something_Recipe or _Something_Picture pattern
                                # Pattern: _Word_Recipe or _Word_Picture (case insensitive)
                                if not re.match(r'^[A-Za-z]+_(recipe|picture)$', word, re.I):
                                    cleaned_words.append(word)
                            title = ' '.join(cleaned_words).strip()
                            
                            # Clean up trailing dashes, extra spaces, etc.
                            title = re.sub(r'\s+-\s*$', '', title)  # Remove trailing " -"
                            title = re.sub(r'-\s*$', '', title)  # Remove trailing "-"
                            title = re.sub(r'\s+$', '', title)  # Remove trailing spaces
                            title = title.strip()
                            
                            # Start new recipe
                            current_recipe = {
                                'title': title,
                                'external_links': [],  # External URLs (non-Google Doc)
                                'google_doc_links': [],  # Google Doc URLs
                                'picture_links': [],  # Picture/image links
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
                                    
                                    # Check if this is a _Recipe link (should be treated as Quick Recipe)
                                    if link_text.lower().endswith('_recipe') and 'docs.google.com' in url:
                                        # This is a Quick Recipe link - will be processed later
                                        if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                            current_recipe['google_doc_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    # Check if this is a _Picture link
                                    elif link_text.lower().endswith('_picture'):
                                        # Picture link - store separately
                                        if not any(l['url'] == url for l in current_recipe['picture_links']):
                                            current_recipe['picture_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    elif 'docs.google.com' in url:
                                        # Other Google Doc link - check for duplicates
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
                                    
                                    # Check if this is a _Recipe link (should be treated as Quick Recipe)
                                    if link_text.lower().endswith('_recipe') and 'docs.google.com' in url:
                                        # This is a Quick Recipe link
                                        if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                            current_recipe['google_doc_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    # Check if this is a _Picture link
                                    elif link_text.lower().endswith('_picture'):
                                        # Picture link - store separately
                                        if not any(l['url'] == url for l in current_recipe['picture_links']):
                                            current_recipe['picture_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    elif 'docs.google.com' in url:
                                        # Other Google Doc link - avoid duplicates
                                        if not any(l['url'] == url for l in current_recipe['google_doc_links']):
                                            current_recipe['google_doc_links'].append({
                                                'text': link_text,
                                                'url': url
                                            })
                                    else:
                                        # External link - avoid duplicates
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
            
            # Load quick recipes from separate document if doc ID provided
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
            
            # Extract Quick Recipe content from Google Doc links
            # Look for Quick_Recipe links or _Recipe links in google_doc_links and fetch their content
            for recipe in self.recipes:
                if not recipe.get('quick_recipe'):  # Only fetch if we don't already have content
                    # Check for Quick_Recipe links or _Recipe links (like Trevor_Recipe, Mom_Recipe)
                    for link in recipe.get('google_doc_links', []):
                        link_text = link.get('text', '').lower()
                        # Check if this link should be treated as a Quick Recipe
                        is_quick_recipe_link = (
                            'quick_recipe' in link_text or 
                            'quick recipe' in link_text or 
                            link_text.endswith('_recipe')
                        )
                        
                        if is_quick_recipe_link:
                            # Extract document ID from URL
                            doc_id = self._extract_doc_id_from_url(link['url'])
                            if doc_id:
                                content, images = self._fetch_google_doc_content(doc_id)
                                if content:
                                    recipe['quick_recipe'] = content
                                    recipe['has_quick_recipe'] = True
                                # Add any images found in the document to picture_links
                                if images:
                                    for img in images:
                                        if not any(p['url'] == img['url'] for p in recipe.get('picture_links', [])):
                                            if 'picture_links' not in recipe:
                                                recipe['picture_links'] = []
                                            recipe['picture_links'].append(img)
                                if content or images:
                                    break  # Use first Quick Recipe link found
            
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
    
    def _extract_doc_id_from_url(self, url: str) -> Optional[str]:
        """Extract Google Doc ID from a URL."""
        # Pattern: https://docs.google.com/document/d/DOC_ID/edit...
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _fetch_google_doc_content(self, doc_id: str) -> Tuple[Optional[str], List[Dict]]:
        """Fetch text content and images from a Google Doc or other document type.
        Returns: (text_content, image_urls) where image_urls is a list of {'url': str, 'text': str}
        """
        try:
            credentials = creds.login()
            
            # First, try Google Docs API (for native Google Docs)
            try:
                docs_service = build('docs', 'v1', credentials=credentials)
                doc = docs_service.documents().get(documentId=doc_id).execute()
                
                content = doc.get('body', {}).get('content', [])
                text_lines = []
                image_urls = []
                
                # Get inline objects (images)
                inline_objects = doc.get('inlineObjects', {})
                
                for element in content:
                    if 'paragraph' in element:
                        para = element.get('paragraph', {})
                        elements = para.get('elements', [])
                        paragraph_text = ''
                        
                        for elem in elements:
                            if 'textRun' in elem:
                                text_run = elem.get('textRun', {})
                                content_text = text_run.get('content', '')
                                # Skip strikethrough text
                                if not text_run.get('textStyle', {}).get('strikethrough', False):
                                    paragraph_text += content_text
                            
                            # Check for inline images
                            if 'inlineObjectElement' in elem:
                                inline_obj = elem.get('inlineObjectElement', {})
                                inline_obj_id = inline_obj.get('inlineObjectId', '')
                                
                                if inline_obj_id in inline_objects:
                                    obj = inline_objects[inline_obj_id]
                                    embedded_obj = obj.get('inlineObjectProperties', {}).get('embeddedObject', {})
                                    image_props = embedded_obj.get('imageProperties', {})
                                    content_uri = image_props.get('contentUri', '')
                                    source_uri = image_props.get('sourceUri', '')
                                    
                                    image_url = content_uri or source_uri
                                    if image_url:
                                        image_urls.append({
                                            'url': image_url,
                                            'text': 'Image'
                                        })
                        
                        if paragraph_text.strip():
                            text = paragraph_text.strip()
                            bullet = para.get('bullet')
                            if bullet is not None:
                                nesting = bullet.get('nestingLevel', 0)
                                indent = '  ' * nesting
                                text_lines.append(f'{indent}- {text}')
                            else:
                                text_lines.append(text)
                
                text_content = '\n'.join(text_lines) if text_lines else None
                return (text_content, image_urls)
                
            except Exception as docs_error:
                # If Docs API fails, try downloading .docx files
                error_msg = str(docs_error)
                if '400' in error_msg or 'not supported' in error_msg.lower():
                    # Try Drive API to download .docx files
                    try:
                        drive_service = build('drive', 'v3', credentials=credentials)
                        # Get file info first
                        file_info = drive_service.files().get(fileId=doc_id, fields='mimeType').execute()
                        mime_type = file_info.get('mimeType', '')
                        
                        # For .docx files, download and parse with python-docx
                        if 'wordprocessingml' in mime_type or 'openxmlformats' in mime_type:
                            # Download the file
                            import io
                            from googleapiclient.http import MediaIoBaseDownload
                            
                            request = drive_service.files().get_media(fileId=doc_id)
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while done is False:
                                status, done = downloader.next_chunk()
                            
                            fh.seek(0)
                            # Parse .docx file
                            try:
                                from docx import Document
                                docx_file = Document(fh)
                                text_lines = []
                                for paragraph in docx_file.paragraphs:
                                    if paragraph.text.strip():
                                        text_lines.append(paragraph.text.strip())
                                text_content = '\n'.join(text_lines) if text_lines else None
                                return (text_content, [])  # .docx files don't have embedded images we can extract easily
                            except ImportError:
                                # python-docx not installed
                                return (None, [])
                    except Exception as drive_error:
                        # Drive download also failed
                        pass
                
                # If both fail, return None
                return (None, [])
            
        except Exception as e:
            # Silently fail - document might not be accessible
            return (None, [])


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

