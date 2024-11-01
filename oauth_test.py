import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def test_gmail_connection():
    """Test Gmail API connection and OAuth setup"""
    try:
        # Initialize OAuth 2.0 flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        
        # Run local server to receive authorization code
        creds = flow.run_local_server(port=0)
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        # Test API by getting user profile
        profile = service.users().getProfile(userId='me').execute()
        
        print("✅ Successfully connected to Gmail API!")
        print(f"Connected email address: {profile['emailAddress']}")
        
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Saved credentials to token.json")
        
        # Test message retrieval
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        messages = results.get('messages', [])
        
        if messages:
            print("✅ Successfully retrieved messages")
        else:
            print("⚠️ No messages found")
            
    except HttpError as error:
        print(f"❌ An error occurred: {error}")
    except Exception as error:
        print(f"❌ An unexpected error occurred: {error}")

if __name__ == '__main__':
    test_gmail_connection()