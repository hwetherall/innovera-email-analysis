import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Email Configuration
PERSONAL_EMAIL = "hwetherall@gmail.com"

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Gmail API Configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] 