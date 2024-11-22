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
from google.auth.transport.requests import Request
import openai
import tkinter as tk
from tkinter import ttk
import threading
from dotenv import load_dotenv

# Add this line near the top of the file, after imports
load_dotenv()

class EmailSync:
    def __init__(self, target_email):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.HOST_EMAIL = "hwetherall@gmail.com"
        self.GUEST_EMAIL = target_email
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
        
        # Check if credentials are valid, if not refresh them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # Refresh the credentials
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)

    def create_query(self):
        """Create Gmail search query for emails between the two specific addresses"""
        return (
            f'(from:{self.HOST_EMAIL} to:{self.GUEST_EMAIL}) OR '
            f'(from:{self.GUEST_EMAIL} to:{self.HOST_EMAIL})'
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
                (from_email == self.HOST_EMAIL and to_email == self.GUEST_EMAIL) or
                (from_email == self.GUEST_EMAIL and to_email == self.HOST_EMAIL)
            ):
                return None
            
            # Determine direction
            direction = 'to_guest' if from_email == self.HOST_EMAIL else 'to_host'
            
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
        except HttpError as e:
            print(f"HTTP error occurred while processing message {message_id}: {e}")
            return None
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
            SUM(CASE WHEN direction = 'to_guest' THEN 1 ELSE 0 END) as to_guest,
            SUM(CASE WHEN direction = 'to_host' THEN 1 ELSE 0 END) as to_host,
            MIN(date) as earliest,
            MAX(date) as latest
        FROM emails
        ''')
        
        stats = self.cursor.fetchone()
        print("\nEmail Statistics:")
        print(f"Total emails synced: {stats[0]}")
        print(f"Emails to guest: {stats[1]}")
        print(f"Emails to host: {stats[2]}")
        if stats[0] > 0:
            print(f"Date range: {stats[3]} to {stats[4]}")

class EmailIntelligence:
    def __init__(self, db_path='innovera_emails.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Try to get API key from environment variable
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
        openai.api_key = self.api_key
        
    def query_emails(self, user_question):
        try:
            # First, get context from the database
            context = self._get_email_context()
            
            # Construct the prompt
            prompt = f"""
            Based on the following email correspondence data:
            {context}
            
            Please answer this question: {user_question}
            """
            
            # Query ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Changed to gpt-4o-mini
                messages=[
                    {"role": "system", "content": "You are an AI assistant analyzing email correspondence."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message['content']
        except openai.error.AuthenticationError:
            return "Error: Invalid OpenAI API key. Please check your API key configuration."
        except Exception as e:
            return f"Error querying OpenAI: {str(e)}"
        
    def _get_email_context(self):
        # Query the database for relevant information
        self.cursor.execute('''
        SELECT date, subject, body, direction
        FROM emails
        ORDER BY date DESC
        ''')
        
        emails = self.cursor.fetchall()
        return "\n\n".join([
            f"Date: {email[0]}\nSubject: {email[1]}\nBody: {email[2]}\nDirection: {email[3]}"
            for email in emails
        ])

class EddieGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EDDIE - Email Intelligence")
        self.root.geometry("800x600")
        
        # Email setup frame
        setup_frame = ttk.LabelFrame(self.root, text="Email Setup", padding=10)
        setup_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Target Email:").pack(side="left")
        self.email_entry = ttk.Entry(setup_frame, width=40)
        self.email_entry.pack(side="left", padx=5)
        ttk.Button(setup_frame, text="Sync Emails", command=self._sync_emails).pack(side="left", padx=5)
        
        # Add status label
        self.status_label = ttk.Label(setup_frame, text="")
        self.status_label.pack(side="left", padx=5)
        
        # Query frame
        query_frame = ttk.LabelFrame(self.root, text="Email Intelligence", padding=10)
        query_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.query_entry = tk.Text(query_frame, height=3)
        self.query_entry.pack(fill="x", pady=5)
        ttk.Button(query_frame, text="Ask EDDIE", command=self._ask_eddie).pack()
        
        # Results area
        self.results_text = tk.Text(query_frame, height=20)
        self.results_text.pack(fill="both", expand=True, pady=5)
        
    def _sync_emails(self):
        target_email = self.email_entry.get()
        if not target_email:
            self.status_label.config(text="Please enter a target email")
            return
            
        def sync():
            try:
                self.status_label.config(text="Syncing emails...")
                syncer = EmailSync(target_email)
                syncer.authenticate()
                syncer.sync_emails()
                self.status_label.config(text="Email sync completed!")
                self.results_text.insert("end", "Email sync completed successfully!\n")
            except Exception as e:
                error_msg = f"Error during sync: {str(e)}\n"
                self.status_label.config(text="Sync failed!")
                self.results_text.insert("end", error_msg)
            
        threading.Thread(target=sync).start()
        
    def _ask_eddie(self):
        question = self.query_entry.get("1.0", "end-1c")
        if not question:
            self.results_text.insert("end", "Please enter a question\n")
            return
            
        def query():
            intelligence = EmailIntelligence()
            response = intelligence.query_emails(question)
            self.results_text.insert("end", f"\nQ: {question}\nA: {response}\n\n")
            
        threading.Thread(target=query).start()
        
    def run(self):
        self.root.mainloop()

def main():
    gui = EddieGUI()
    gui.run()

if __name__ == "__main__":
    main()