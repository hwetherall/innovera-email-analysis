import sqlite3
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import re
from wordcloud import WordCloud

class EmailAnalyzer:
    def __init__(self, db_path='innovera_emails.db'):
        self.conn = sqlite3.connect(db_path)
        # Convert database rows directly to pandas DataFrame
        self.df = pd.read_sql_query("""
            SELECT * FROM emails
            ORDER BY date ASC
        """, self.conn)
        # Convert date string to datetime
        self.df['date'] = pd.to_datetime(self.df['date'])

    def get_basic_stats(self):
        """Get basic statistics about email communication"""
        stats = {
            'total_threads': self.df['thread_id'].nunique(),
            'avg_response_time': self._calculate_avg_response_time(),
            'busiest_month': self._get_busiest_month(),
            'common_subjects': self._get_common_subjects(),
            'email_volume_by_year': self._get_volume_by_year()
        }
        return stats

    def _calculate_avg_response_time(self):
        """Calculate average response time within threads"""
        response_times = []
        for thread_id in self.df['thread_id'].unique():
            thread_msgs = self.df[self.df['thread_id'] == thread_id].sort_values('date')
            if len(thread_msgs) > 1:
                time_diffs = thread_msgs['date'].diff()
                response_times.extend(time_diffs.dropna().dt.total_seconds() / 3600)  # Convert to hours
        
        if response_times:
            return sum(response_times) / len(response_times)
        return 0

    def _get_busiest_month(self):
        """Find the month with most email activity"""
        monthly_counts = self.df.groupby(self.df['date'].dt.strftime('%Y-%m')).size()
        return monthly_counts.idxmax(), monthly_counts.max()

    def _get_common_subjects(self, top_n=5):
        """Get most common email subject patterns"""
        # Remove Re:, Fwd:, etc. and group similar subjects
        cleaned_subjects = self.df['subject'].str.replace(r'^(Re|Fwd|FW|RE):\s*', '', regex=True)
        return cleaned_subjects.value_counts().head(top_n).to_dict()

    def _get_volume_by_year(self):
        """Get email volume by year"""
        return self.df.groupby(self.df['date'].dt.year).size().to_dict()

    def generate_insights_report(self):
        """Generate a comprehensive insights report"""
        stats = self.get_basic_stats()
        
        report = f"""
Email Communication Analysis Report
=================================

Overall Statistics:
------------------
• Total email threads: {stats['total_threads']}
• Average response time: {stats['avg_response_time']:.2f} hours
• Busiest month: {stats['busiest_month'][0]} with {stats['busiest_month'][1]} emails

Communication Patterns:
----------------------
• Email volume by year:
"""
        for year, count in stats['email_volume_by_year'].items():
            report += f"  - {year}: {count} emails\n"

        report += "\nCommon Discussion Topics:\n"
        for subject, count in stats['common_subjects'].items():
            report += f"  - {subject}: {count} occurrences\n"

        # Add time analysis
        hour_distribution = self.df['date'].dt.hour.value_counts().sort_index()
        peak_hour = hour_distribution.idxmax()
        report += f"\nTime Analysis:\n-------------\n"
        report += f"• Peak activity hour: {peak_hour}:00"

        return report

    def plot_email_patterns(self):
        """Generate visualizations of email patterns"""
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Email volume over time
        self.df.resample('M', on='date').size().plot(ax=ax1, title='Email Volume Over Time')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Number of Emails')
        
        # 2. Email direction distribution
        self.df['direction'].value_counts().plot(kind='pie', ax=ax2, title='Email Direction Distribution')
        
        # 3. Hourly distribution
        self.df['date'].dt.hour.value_counts().sort_index().plot(
            kind='bar', ax=ax3, title='Email Activity by Hour')
        ax3.set_xlabel('Hour of Day')
        ax3.set_ylabel('Number of Emails')
        
        # 4. Monthly distribution
        self.df['date'].dt.month.value_counts().sort_index().plot(
            kind='bar', ax=ax4, title='Email Activity by Month')
        ax4.set_xlabel('Month')
        ax4.set_ylabel('Number of Emails')
        
        plt.tight_layout()
        plt.savefig('email_patterns.png')
        plt.close()

def main():
    analyzer = EmailAnalyzer()
    
    # Generate and print insights report
    print(analyzer.generate_insights_report())
    
    # Generate visualizations
    analyzer.plot_email_patterns()
    print("\nVisualizations have been saved to 'email_patterns.png'")

if __name__ == "__main__":
    main()