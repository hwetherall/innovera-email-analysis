import sqlite3
import pandas as pd
import numpy as np  # Added numpy import

import matplotlib.pyplot as plt
from datetime import datetime

class InnoveraEmailAnalyzer:
    def __init__(self, db_path='innovera_domain_emails.db'):
        self.conn = sqlite3.connect(db_path)
        # Read all emails into a DataFrame
        self.df = pd.read_sql_query("""
            SELECT 
                recipient,
                date,
                time,
                subject,
                body,
                direction
            FROM innovera_emails
            ORDER BY date, time
        """, self.conn)
        
        # Convert date and time columns to datetime
        self.df['datetime'] = pd.to_datetime(self.df['date'] + ' ' + self.df['time'])

    def generate_visualizations(self):
        """Create comprehensive email pattern visualizations"""
        # Set figure size and create subplots
        fig = plt.figure(figsize=(15, 10))
        
        # Create a 2x2 grid of subplots
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. Email Volume Over Time
        ax1 = fig.add_subplot(gs[0, :])
        monthly_counts = self.df.resample('M', on='datetime').size()
        ax1.plot(monthly_counts.index, monthly_counts.values, marker='o', color='royalblue', linewidth=2)
        ax1.set_title('Email Volume Over Time', fontsize=12, pad=15)
        ax1.set_xlabel('Date', fontsize=10)
        ax1.set_ylabel('Number of Emails', fontsize=10)
        ax1.grid(True, linestyle='--', alpha=0.7)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. Email Distribution by Recipient
        ax2 = fig.add_subplot(gs[1, 0])
        recipient_counts = self.df['recipient'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(recipient_counts)))
        ax2.pie(recipient_counts.values, labels=recipient_counts.index, 
                autopct='%1.1f%%', colors=colors, startangle=90)
        ax2.set_title('Email Distribution by Recipient', fontsize=12, pad=15)
        
        # 3. Email Activity by Hour
        ax3 = fig.add_subplot(gs[1, 1])
        hourly_counts = self.df['datetime'].dt.hour.value_counts().sort_index()
        bars = ax3.bar(hourly_counts.index, hourly_counts.values, 
                      color='lightcoral', alpha=0.7)
        ax3.set_title('Email Activity by Hour', fontsize=12, pad=15)
        ax3.set_xlabel('Hour of Day', fontsize=10)
        ax3.set_ylabel('Number of Emails', fontsize=10)
        ax3.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('innovera_email_patterns.png', dpi=300, bbox_inches='tight')
        plt.close()

    def export_csv(self):
        """Export emails to a clean CSV format"""
        # Create a clean DataFrame for export
        export_df = self.df.copy()
        
        # Format the body text (remove excessive newlines, etc.)
        export_df['body'] = export_df['body'].apply(lambda x: ' '.join(x.split()) if isinstance(x, str) else x)
        
        # Sort by datetime
        export_df = export_df.sort_values('datetime')
        
        # Select and rename columns for export
        export_df = export_df[[
            'recipient',
            'datetime',
            'subject',
            'body',
            'direction'
        ]].rename(columns={
            'datetime': 'Date & Time'
        })
        
        # Export to CSV
        export_df.to_csv('innovera_correspondence.csv', index=False, encoding='utf-8')
        
        return len(export_df)

    def print_report(self):
        """Print a comprehensive analysis report"""
        print("\nInnovera Email Analysis Report")
        print("=============================")
        
        # Basic statistics
        total_emails = len(self.df)
        unique_recipients = self.df['recipient'].nunique()
        
        print(f"\nTotal Emails: {total_emails}")
        print(f"Unique Recipients: {unique_recipients}")
        
        if total_emails > 0:
            print(f"Date Range: {self.df['datetime'].min():%Y-%m-%d} to {self.df['datetime'].max():%Y-%m-%d}")
            
            # Emails per recipient
            print("\nEmails per Recipient:")
            recipient_counts = self.df['recipient'].value_counts()
            for recipient, count in recipient_counts.items():
                print(f"  - {recipient}: {count} emails")
            
            # Most active times
            busiest_hour = self.df['datetime'].dt.hour.mode().iloc[0]
            print(f"\nMost Active Hour: {busiest_hour:02d}:00")
        
        print("\nFiles Generated:")
        print("1. innovera_email_patterns.png - Visualization of email patterns")
        print("2. innovera_correspondence.csv - Complete email correspondence")

def main():
    print("Starting Innovera email analysis...")
    analyzer = InnoveraEmailAnalyzer()
    
    # Generate visualizations
    print("Generating email pattern visualizations...")
    analyzer.generate_visualizations()
    
    # Export CSV
    print("Exporting correspondence to CSV...")
    num_emails = analyzer.export_csv()
    
    # Print report
    analyzer.print_report()

if __name__ == "__main__":
    main()