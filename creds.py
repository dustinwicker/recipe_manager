from google.oauth2.service_account import Credentials
import os

credentials = None

def login():
    """
    Login to access Google Sheets and Google Drive.
    Returns:
        creds: Credentials object.
    """
    global credentials
    SCOPES = ['https://www.googleapis.com/auth/documents',
              'https://www.googleapis.com/auth/drive',
              'https://www.googleapis.com/auth/spreadsheets'
              ]
    if credentials is None:
        credentials = Credentials.from_service_account_file(
            os.environ.get('GOOGLE_SERVICE_ACCOUNT'), 
            scopes=SCOPES)
    return credentials
