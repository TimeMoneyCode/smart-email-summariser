import imaplib
import email
import os
import logging
from email.header import decode_header
from typing import List, Tuple, Optional
from transformers import pipeline
import openai
import getpass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def authenticate_imap(server: str, email_user: str, password: str) -> imaplib.IMAP4_SSL:
    """Authenticate to IMAP server."""
    try:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(email_user, password)
        logging.info("Authenticated successfully.")
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f"IMAP authentication failed: {e}")
        raise


def fetch_emails(
    mail: imaplib.IMAP4_SSL, n: int = 5, unread_only: bool = True
) -> List[Tuple[str, bytes]]:
    """Fetch unread or latest N emails."""
    mail.select("inbox")
    if unread_only:
        status, messages = mail.search(None, "UNSEEN")
    else:
        status, messages = mail.search(None, "ALL")
    if status != "OK":
        logging.error("Failed to fetch emails.")
        return []
    email_ids = messages[0].split()
    email_ids = email_ids[-n:]
    fetched = []
    for eid in email_ids:
        status, msg_data = mail.fetch(eid, "(RFC822)")
        if status == "OK":
            fetched.append((eid, msg_data[0][1]))
    return fetched


def extract_email_content(raw_email: bytes) -> Tuple[str, str, str]:
    """Extract sender, subject, and body from raw email."""
    msg = email.message_from_bytes(raw_email)
    sender = msg.get("From", "")
    subject, encoding = decode_header(msg.get("Subject", ""))[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                charset = part.get_content_charset() or "utf-8"
                body = part.get_payload(decode=True).decode(charset, errors="ignore")
                break
        else:
            # Fallback to HTML
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(
                        charset, errors="ignore"
                    )
                    break
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        elif content_type == "text/html":
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
    return sender, subject, body


def summarize_text(
    text: str, method: str = "transformer", openai_api_key: Optional[str] = None
) -> str:
    """Summarize text using transformer or OpenAI API."""
    if method == "openai" and openai_api_key:
        openai.api_key = openai_api_key
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Summarize the following email:"},
                    {"role": "user", "content": text},
                ],
                max_tokens=100,
            )
            return response.choices[0].message["content"].strip()
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return "[Summary unavailable due to API error]"
    elif method == "transformer":
        try:
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            summary = summarizer(text, max_length=100, min_length=20, do_sample=False)
            return summary[0]["summary_text"]
        except Exception as e:
            logging.error(f"Transformer summarization error: {e}")
            return "[Summary unavailable due to summarization error]"
    else:
        return "[No summarization method available]"


def try_summarize_text(
    text: str, method: str = "transformer", openai_api_key: Optional[str] = None
) -> str:
    """Try to summarize text, retrying once if the first attempt fails."""
    summary = summarize_text(text, method=method, openai_api_key=openai_api_key)
    if summary.startswith("[Summary unavailable"):
        logging.info("First summarization attempt failed, retrying...")
        summary = summarize_text(text, method=method, openai_api_key=openai_api_key)
    return summary


def output_summary(
    sender: str, subject: str, summary: str, save_file: Optional[str] = None
):
    output = f"From: {sender}\nSubject: {subject}\nSummary: {summary}\n{'-'*40}"
    print(output)
    if save_file:
        with open(save_file, "a", encoding="utf-8") as f:
            f.write(output + "\n")


def mark_as_read(mail: imaplib.IMAP4_SSL, email_id: str):
    mail.store(email_id, "+FLAGS", "\\Seen")


def main():
    print("Smart Email Summarizer (interactive mode)")
    server = input("IMAP server (e.g., imap.gmail.com): ").strip()
    user = input("Email address: ").strip()
    # Loop for password until authentication succeeds
    while True:
        password = getpass.getpass("App password or IMAP password: ").strip()
        try:
            mail = authenticate_imap(server, user, password)
            break
        except imaplib.IMAP4.error:
            print("Authentication failed. Please try again.")
    method = (
        input("Summarization method (transformer/openai) [transformer]: ").strip()
        or "transformer"
    )
    n = input("Number of emails to summarize [5]: ").strip()
    n = int(n) if n.isdigit() else 5
    unread_only = input("Only fetch unread emails? (y/n) [y]: ").strip().lower() != "n"
    mark_read = (
        input("Mark emails as read after summarizing? (y/n) [n]: ").strip().lower()
        == "y"
    )
    save_file = input("File to save summaries (leave blank for none): ").strip() or None
    openai_api_key = None
    if method == "openai":
        openai_api_key = input("OpenAI API key: ").strip()

    emails = fetch_emails(mail, n=n, unread_only=unread_only)
    if not emails:
        logging.info("No emails found.")
        return
    for eid, raw_email in emails:
        sender, subject, body = extract_email_content(raw_email)
        if not body.strip():
            logging.warning(
                f"Email from {sender} with subject '{subject}' has no body."
            )
            continue
        summary = try_summarize_text(body, method=method, openai_api_key=openai_api_key)
        output_summary(sender, subject, summary, save_file=save_file)
        if mark_read:
            mark_as_read(mail, eid)
    mail.logout()


if __name__ == "__main__":
    main()
