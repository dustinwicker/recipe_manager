#!/usr/bin/env python3
"""
Check document permissions and test link extraction.
"""

import creds
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def check_document_access(doc_id):
    """Check if we can access the document and see links."""
    credentials = creds.login()
    service = build('docs', 'v1', credentials=credentials)
    
    try:
        print(f"Checking access to document: {doc_id}\n")
        doc = service.documents().get(documentId=doc_id).execute()
        
        title = doc.get('title', 'Unknown')
        print(f"✓ Document accessible: {title}\n")
        
        # Check for links
        content = doc.get('body', {}).get('content', [])
        link_count = 0
        external_link_count = 0
        
        for element in content:
            if 'paragraph' in element:
                para = element.get('paragraph', {})
                elements = para.get('elements', [])
                
                for elem in elements:
                    if 'textRun' in elem:
                        text_run = elem.get('textRun', {})
                        if 'link' in text_run:
                            link = text_run.get('link', {})
                            if 'url' in link:
                                link_count += 1
                                url = link['url']
                                if 'docs.google.com' not in url:
                                    external_link_count += 1
                                    if external_link_count <= 5:  # Show first 5
                                        text = text_run.get('content', '').strip()
                                        print(f"  External link found: '{text}' -> {url}")
        
        print(f"\nTotal links found: {link_count}")
        print(f"External links: {external_link_count}")
        
        if link_count == 0:
            print("\n⚠️  WARNING: No links found in document!")
            print("This could mean:")
            print("  1. The document doesn't have any hyperlinks")
            print("  2. The service account doesn't have permission to read links")
            print("  3. Links are stored in a format the API doesn't expose")
            print("\nService account email: self-550@creds-443417.iam.gserviceaccount.com")
            print("Make sure this email has 'Viewer' or 'Editor' access to the document.")
        
        return link_count > 0
        
    except HttpError as e:
        if e.resp.status == 403:
            print("✗ ERROR: Permission denied (403)")
            print("The service account doesn't have access to this document.")
            print("\nService account email: self-550@creds-443417.iam.gserviceaccount.com")
            print("Please share the document with this email address.")
        else:
            print(f"✗ ERROR: {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    doc_id = '1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY'
    check_document_access(doc_id)

