Smart Email Summarizer
======================

This Python script connects to your email inbox via IMAP, fetches emails, and summarizes their content using either a local transformer model or the OpenAI GPT API.

Features
--------
- Secure IMAP authentication (password hidden, retries on failure)
- Fetches unread or latest N emails
- Extracts sender, subject, and body (prefers plain text)
- Summarizes emails using Hugging Face transformers (facebook/bart-large-cnn) or OpenAI GPT
- Outputs summaries to the console and optionally saves to a file
- Interactive prompts for all settings
- Graceful error handling and retry logic for summarization

Requirements
------------
- Python 3.7+
- See `requirements.txt` for dependencies

Setup
-----
1. Install dependencies:
   pip install -r requirements.txt

2. Run the script:
   python smart_email_summarizer.py

3. Follow the interactive prompts:
   - IMAP server (e.g., imap.gmail.com)
   - Email address
   - App password (input is hidden)
   - Summarization method (transformer/openai)
   - Number of emails to summarize
   - Other options as prompted

Notes
-----
- The first run with the transformer method will download a large model (~1.5GB).
- For OpenAI summarization, you need an API key.
- Your password is never shown on screen and is not stored.
- If authentication fails, you will be prompted to try again.

Troubleshooting
---------------
- If you see errors about missing packages, ensure you installed all dependencies.
- For Gmail, you may need to use an app password and enable IMAP in your account settings.
- If summarization fails, the script will retry once automatically.

License
-------
MIT License
