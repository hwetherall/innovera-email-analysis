# innovera-email-analysis

# Innovera Email Analysis Tool

Automated tool for analyzing email communications between Gmail and Innovera domains. This tool provides visualization and analysis of email patterns, communication frequency, and content extraction.

## Features

- Gmail API integration
- Automated email syncing
- Communication pattern analysis
- Visual analytics
- CSV export functionality

## Prerequisites

- Python 3.x
- Gmail account
- Google Cloud Project with Gmail API enabled

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hwetherall/innovera-email-analysis.git
cd innovera-email-analysis
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials and save as `credentials.json` in the project directory

## Usage

1. First, sync your emails:
```bash
python email_sync.py
```

2. Generate analysis and visualizations:
```bash
python analyze_emails.py
```

## Output Files

The tool generates several output files:
- `innovera_email_patterns.png`: Visualization of email patterns
- `innovera_correspondence.csv`: Detailed email correspondence data
- `innovera_domain_emails.db`: SQLite database containing raw email data

## Configuration

To modify email addresses or domain, edit the following in `email_sync.py`:
```python
self.PERSONAL_EMAIL = "your.email@gmail.com"
self.INNOVERA_DOMAIN = "@innovera.ai"
```

## Security Note

This tool requires access to your Gmail account through OAuth 2.0. It only reads email data and stores it locally. No data is transmitted to external servers.

## Contributing

This is a private repository for Innovera internal use. Please contact the repository owner for access or contribution guidelines.

## License

Private - All rights reserved
