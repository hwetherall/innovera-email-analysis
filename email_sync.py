import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sqlite3
from datetime import datetime
import json
import base64
from email.utils import parseaddr

class EmailSync:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.PERSONAL_EMAIL = "hwetherall@gmail.com"
        self.WORK_EMAIL = "harry@innovera.ai"
        self.setup_database()

    def setup_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('innovera_emails.db')
        self.cursor = self.conn.cursor()
        
        # Drop existing table to start fresh
        self.cursor.execute('DROP TABLE IF EXISTS emails')
        
        # Create emails table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            thread_id TEXT,
            subject TEXT,
            from_email TEXT,
            to_email TEXT,
            date TIMESTAMP,
            body TEXT,
            direction TEXT
        )
        ''')
        self.conn.commit()

    def authenticate(self):
        """Handle Gmail OAuth authentication"""
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)

    def create_query(self):
        """Create Gmail search query for emails between the two specific addresses"""
        # More precise query to only get emails between these two addresses
        return (
            f'(from:{self.PERSONAL_EMAIL} to:{self.WORK_EMAIL}) OR '
            f'(from:{self.WORK_EMAIL} to:{self.PERSONAL_EMAIL})'
        )

    def extract_email_content(self, message):
        """Extract the plain text content from email message"""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(
                            part['body']['data']).decode('utf-8')
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            return base64.urlsafe_b64decode(
                message['payload']['body']['data']).decode('utf-8')
        return ""

    def process_message(self, message_id):
        """Process a single email message with strict filtering"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            
            # Clean and extract email addresses
            from_email = parseaddr(from_email)[1].lower()
            to_email = parseaddr(to_email)[1].lower()
            
            # Strict filtering: Only process if it's directly between our two addresses
            if not (
                (from_email == self.PERSONAL_EMAIL and to_email == self.WORK_EMAIL) or
                (from_email == self.WORK_EMAIL and to_email == self.PERSONAL_EMAIL)
            ):
                return None
            
            # Determine direction
            direction = 'to_work' if from_email == self.PERSONAL_EMAIL else 'to_personal'
            
            body = self.extract_email_content(message)
            date = datetime.fromtimestamp(int(message['internalDate'])/1000)
            
            return {
                'message_id': message_id,
                'thread_id': message['threadId'],
                'subject': subject,
                'from_email': from_email,
                'to_email': to_email,
                'date': date,
                'body': body,
                'direction': direction
            }
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")
            return None

    def store_email(self, email_data):
        """Store email in database"""
        if not email_data:
            return
            
        self.cursor.execute('''
        INSERT OR REPLACE INTO emails 
        (message_id, thread_id, subject, from_email, to_email, date, body, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data['message_id'],
            email_data['thread_id'],
            email_data['subject'],
            email_data['from_email'],
            email_data['to_email'],
            email_data['date'],
            email_data['body'],
            email_data['direction']
        ))
        self.conn.commit()

    def sync_emails(self):
        """Sync emails between the two specific addresses"""
        print("Starting email sync...")
        query = self.create_query()
        processed_count = 0
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                print("No messages found between the specified email addresses.")
                return
                
            total_messages = len(messages)
            print(f"Found {total_messages} messages to process...")
            
            for message in messages:
                email_data = self.process_message(message['id'])
                if email_data:
                    self.store_email(email_data)
                    processed_count += 1
                    print(f"Processed {processed_count}/{total_messages} emails...")
            
            print(f"\nSync completed! Processed {processed_count} emails.")
            self.print_stats()
            
        except HttpError as error:
            print(f"An error occurred: {error}")

    def print_stats(self):
        """Print email statistics"""
        self.cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN direction = 'to_work' THEN 1 ELSE 0 END) as to_work,
            SUM(CASE WHEN direction = 'to_personal' THEN 1 ELSE 0 END) as to_personal,
            MIN(date) as earliest,
            MAX(date) as latest
        FROM emails
        ''')
        
        stats = self.cursor.fetchone()
        print("\nEmail Statistics:")
        print(f"Total emails synced: {stats[0]}")
        print(f"Emails to work: {stats[1]}")
        print(f"Emails to personal: {stats[2]}")
        if stats[0] > 0:
            print(f"Date range: {stats[3]} to {stats[4]}")

def main():
    syncer = EmailSync()
    syncer.authenticate()
    syncer.sync_emails()

if __name__ == "__main__":
    main()