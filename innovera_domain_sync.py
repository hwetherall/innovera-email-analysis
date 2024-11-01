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
import re

class InnoveraEmailSync:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.PERSONAL_EMAIL = "hwetherall@gmail.com"
        self.INNOVERA_DOMAIN = "@innovera.ai"
        self.setup_database()

    def setup_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('innovera_domain_emails.db')
        self.cursor = self.conn.cursor()
        
        # Drop existing table to start fresh
        self.cursor.execute('DROP TABLE IF EXISTS innovera_emails')
        
        # Create emails table with recipient column
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS innovera_emails (
            message_id TEXT PRIMARY KEY,
            recipient TEXT,
            date DATE,
            time TIME,
            subject TEXT,
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
        """Create Gmail search query for emails with innovera.ai domain"""
        return (
            f'(from:{self.PERSONAL_EMAIL} to:{self.INNOVERA_DOMAIN}) OR '
            f'(from:{self.INNOVERA_DOMAIN} to:{self.PERSONAL_EMAIL})'
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
        """Process a single email message with innovera.ai domain filtering"""
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
            
            # Determine if this is a relevant email and get the innovera recipient
            innovera_recipient = None
            direction = None
            
            if from_email == self.PERSONAL_EMAIL and self.INNOVERA_DOMAIN in to_email:
                innovera_recipient = to_email
                direction = 'outbound'
            elif self.INNOVERA_DOMAIN in from_email and to_email == self.PERSONAL_EMAIL:
                innovera_recipient = from_email
                direction = 'inbound'
            else:
                return None
            
            # Extract timestamp and convert to date and time
            timestamp = datetime.fromtimestamp(int(message['internalDate'])/1000)
            date = timestamp.strftime('%Y-%m-%d')
            time = timestamp.strftime('%H:%M:%S')
            
            body = self.extract_email_content(message)
            
            return {
                'message_id': message_id,
                'recipient': innovera_recipient,
                'date': date,
                'time': time,
                'subject': subject,
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
        INSERT OR REPLACE INTO innovera_emails 
        (message_id, recipient, date, time, subject, body, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data['message_id'],
            email_data['recipient'],
            email_data['date'],
            email_data['time'],
            email_data['subject'],
            email_data['body'],
            email_data['direction']
        ))
        self.conn.commit()

    def sync_emails(self):
        """Sync all emails with innovera.ai domain"""
        print("Starting email sync for innovera.ai domain...")
        query = self.create_query()
        processed_count = 0
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                print("No messages found with innovera.ai domain.")
                return
                
            total_messages = len(messages)
            print(f"Found {total_messages} messages to process...")
            
            # Track unique recipients
            recipients = set()
            
            for message in messages:
                email_data = self.process_message(message['id'])
                if email_data:
                    self.store_email(email_data)
                    recipients.add(email_data['recipient'])
                    processed_count += 1
                    print(f"Processed {processed_count}/{total_messages} emails...")
            
            print(f"\nSync completed! Processed {processed_count} emails.")
            print("\nUnique Innovera recipients found:")
            for recipient in sorted(recipients):
                print(f"- {recipient}")
            
            self.print_stats()
            
        except HttpError as error:
            print(f"An error occurred: {error}")

    def print_stats(self):
        """Print email statistics"""
        self.cursor.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT recipient) as unique_recipients,
            MIN(date) as earliest,
            MAX(date) as latest
        FROM innovera_emails
        ''')
        
        stats = self.cursor.fetchone()
        print("\nEmail Statistics:")
        print(f"Total emails synced: {stats[0]}")
        print(f"Unique recipients: {stats[1]}")
        if stats[0] > 0:
            print(f"Date range: {stats[2]} to {stats[3]}")
            
        # Show emails per recipient
        print("\nEmails per recipient:")
        self.cursor.execute('''
        SELECT recipient, COUNT(*) as count
        FROM innovera_emails
        GROUP BY recipient
        ORDER BY count DESC
        ''')
        
        for recipient, count in self.cursor.fetchall():
            print(f"- {recipient}: {count} emails")

def main():
    syncer = InnoveraEmailSync()
    syncer.authenticate()
    syncer.sync_emails()

if __name__ == "__main__":
    main()