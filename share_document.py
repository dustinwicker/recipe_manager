#!/usr/bin/env python3
"""
Helper script to get the service account email for sharing Google Docs/Sheets.
"""

import creds
import json
import os
import sys

def get_service_account_email():
    """Get the service account email from credentials."""
    service_account_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
    
    if not service_account_file:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT environment variable not set")
        return None
    
    try:
        with open(service_account_file, 'r') as f:
            creds_data = json.load(f)
            service_account_email = creds_data.get('client_email')
            return service_account_email
    except FileNotFoundError:
        print(f"ERROR: Service account file not found: {service_account_file}")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in service account file: {service_account_file}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    """Main function."""
    print("="*60)
    print("GOOGLE DOCS/SHEETS SHARING HELPER")
    print("="*60)
    print()
    
    service_account_email = get_service_account_email()
    
    if not service_account_email:
        sys.exit(1)
    
    print(f"Service Account Email: {service_account_email}")
    print()
    print("="*60)
    print("INSTRUCTIONS TO SHARE YOUR DOCUMENT:")
    print("="*60)
    print()
    print("1. Open your Google Doc/Sheet in your browser")
    print("2. Click the 'Share' button (top right)")
    print("3. In the 'Add people and groups' field, paste this email:")
    print()
    print(f"   {service_account_email}")
    print()
    print("4. Set the permission to 'Viewer' (or 'Editor' if you want the")
    print("   script to be able to modify the document)")
    print("5. Click 'Send' (you can uncheck 'Notify people' if you want)")
    print()
    print("="*60)
    print()
    
    # If document ID provided, show specific instructions
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        print(f"Document ID: {doc_id}")
        print(f"Document URL: https://docs.google.com/document/d/{doc_id}/edit")
        print()


if __name__ == "__main__":
    main()

