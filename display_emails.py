import sqlite3
from datetime import datetime
import pandas as pd
pd.set_option('display.max_colwidth', None)  # Show full content
pd.set_option('display.max_rows', None)      # Show all rows

def display_emails():
    # Connect to the database
    conn = sqlite3.connect('innovera_emails.db')
    
    # Query to get emails in chronological order
    query = """
    SELECT 
        date,
        subject,
        body
    FROM emails 
    ORDER BY date ASC
    """
    
    # Read into DataFrame
    df = pd.read_sql_query(query, conn)
    
    # Convert date string to datetime and create separate date and time columns
    df['datetime'] = pd.to_datetime(df['date'])
    df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
    df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
    
    # Reorder columns and drop the datetime column
    df = df[['date', 'time', 'subject', 'body']]
    
    # Save to CSV for easy viewing/searching
    df.to_csv('email_contents.csv', index=False)
    
    # Save to a more readable text format
    with open('email_contents.txt', 'w', encoding='utf-8') as f:
        f.write("Email Communications Log\n")
        f.write("=======================\n\n")
        
        for _, row in df.iterrows():
            f.write(f"Date: {row['date']}\n")
            f.write(f"Time: {row['time']}\n")
            f.write(f"Subject: {row['subject']}\n")
            f.write("-" * 50 + "\n")
            f.write(f"{row['body']}\n")
            f.write("=" * 80 + "\n\n")

    return df

def main():
    print("Generating email content files...")
    df = display_emails()
    print("\nFiles generated:")
    print("1. email_contents.csv - For spreadsheet viewing")
    print("2. email_contents.txt - For easy reading")
    
    # Display a preview of the first few emails
    print("\nPreview of first few emails:")
    preview = df.head()
    for _, row in preview.iterrows():
        print("\n" + "=" * 80)
        print(f"Date: {row['date']}")
        print(f"Time: {row['time']}")
        print(f"Subject: {row['subject']}")
        print("-" * 50)
        print(f"{row['body'][:500]}...")  # Show first 500 characters of body

if __name__ == "__main__":
    main()
    